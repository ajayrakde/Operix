"""JSON-RPC client to the OculiX JVM bridge over stdin/stdout.

The bridge is a fat JAR (~160 MB) containing oculixapi + Apertix OpenCV +
our minimal RPC server. It's downloaded once from GitHub Releases on first
use and cached under ``~/.oculix/lib/``.
"""

from __future__ import annotations

import atexit
import json
import os
import shutil
import subprocess
import threading
import queue
import collections
import urllib.request
import weakref
from pathlib import Path
from typing import Any, Optional, Type

# --- bridge JAR distribution -------------------------------------------------

BRIDGE_VERSION = "1.2.0b1"
BRIDGE_JAR_NAME = f"operix-jvm-bridge-{BRIDGE_VERSION}.jar"
BRIDGE_JAR_URL = (
    "https://github.com/ajayrakde/Operix/releases/download/"
    f"jvm-bridge-{BRIDGE_VERSION}/{BRIDGE_JAR_NAME}"
)
JAR_DIR = Path(os.path.expanduser("~/.oculix/lib/ajayrakde-operix"))


def _ensure_jar() -> Path:
    jar_path = JAR_DIR / BRIDGE_JAR_NAME
    if jar_path.exists():
        return jar_path
    JAR_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[OculiX] Downloading {BRIDGE_JAR_NAME} (~160 MB)…")
    # Download atomically: interrupted installs must not leave a cached broken JAR.
    import tempfile
    temp = None
    try:
        with tempfile.NamedTemporaryFile(dir=JAR_DIR, suffix=".part", delete=False) as stream:
            temp = Path(stream.name)
        urllib.request.urlretrieve(BRIDGE_JAR_URL, temp)
        import zipfile
        with zipfile.ZipFile(temp) as archive:
            if "org/operix/rpc/Server.class" not in archive.namelist():
                raise RuntimeError("Downloaded JAR does not contain the Operix bridge")
        os.replace(temp, jar_path)
    finally:
        if temp is not None and temp.exists(): temp.unlink()
    print(f"[OculiX] Saved to {jar_path}")
    return jar_path


# --- JSON-RPC client ---------------------------------------------------------

class BridgeError(RuntimeError):
    """Raised when the JVM side returned an error for a request."""


class Bridge:
    """Owns the JVM child process and serialises RPC requests over stdio."""

    def __init__(self, jar_path: Optional[Path] = None, java_bin: str = "java"):
        if shutil.which(java_bin) is None:
            raise RuntimeError(
                f"{java_bin!r} not found on PATH. Install Java 11+ "
                "(https://adoptium.net) and retry."
            )
        self._jar = jar_path or _ensure_jar()
        self._java = java_bin
        self._proc: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self._next_id = 0
        self._pending = {}
        self._callbacks = {}
        self._stderr_tail = collections.deque(maxlen=100)
        self._callback_errors = collections.deque(maxlen=100)
        # Python-side identity dedup: same Java ref always yields the same
        # Python object so __del__ doesn't kill a ref that's still in use.
        self._cache: "weakref.WeakValueDictionary[str, Any]" = (
            weakref.WeakValueDictionary())

    def start(self) -> None:
        if self._proc is not None:
            return
        self._proc = subprocess.Popen(
            # Force the JVM to speak UTF-8 on stdio. On Windows the JVM defaults
            # System.out to the console code page (cp1252), so any accented OCR
            # text (é -> 0xe9) is invalid UTF-8 and crashes the reader below.
            # -Dstdout/stderr.encoding (Java 18+) pin the console streams; the
            # file.encoding flag covers older JVMs.
            [self._java,
             "-Dfile.encoding=UTF-8",
             "-Dstdout.encoding=UTF-8",
             "-Dstderr.encoding=UTF-8",
             "-jar", str(self._jar)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=1,           # line buffered
            text=True,
            encoding="utf-8",
            errors="replace",    # belt-and-suspenders: never crash on a stray byte
        )
        threading.Thread(target=self._read_responses, daemon=True, name="operix-rpc").start()
        threading.Thread(target=self._read_stderr, daemon=True, name="operix-stderr").start()
        atexit.register(self.stop)

    def stop(self) -> None:
        if self._proc is None:
            return
        try:
            self._proc.stdin.close()
        except Exception:
            pass
        try:
            self._proc.terminate()
            self._proc.wait(timeout=5)
        except Exception:
            self._proc.kill()
        self._proc = None
        self._callbacks.clear()

    def _read_stderr(self):
        proc = self._proc
        for line in proc.stderr:
            self._stderr_tail.append(line.rstrip())

    def _read_responses(self):
        proc = self._proc
        try:
            for line in proc.stdout:
                response = json.loads(line)
                if "callback" in response:
                    threading.Thread(target=self._handle_callback, args=(response,), daemon=True).start()
                    continue
                with self._lock:
                    pending = self._pending.pop(response.get("id"), None)
                if pending is not None: pending.put(response)
        except Exception as error:
            self._stderr_tail.append(str(error))
        finally:
            with self._lock:
                pending = list(self._pending.values())
                self._pending.clear()
            for waiter in pending:
                waiter.put({"error": "JVM bridge died. stderr: " + "\n".join(self._stderr_tail)})

    def _write(self, payload):
        self._proc.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
        self._proc.stdin.flush()

    def _handle_callback(self, message):
        reply = {"callback_result": message["callback_id"]}
        try:
            callback = self._callbacks[message["callback"]]
            result = callback.dispatch(message["method"], _decode(self, message["args"]))
            reply["result"] = _encode(result, self)
        except Exception as error:
            reply["error"] = type(error).__name__ + ": " + str(error)
            self._callback_errors.append(error)
        try:
            with self._lock: self._write(reply)
        except Exception:
            pass

    def _encode_callback(self, callback):
        key = "p" + str(id(callback))
        self._callbacks[key] = callback
        return {"__callback": key, "interface": callback.interface}

    @property
    def callback_errors(self):
        return tuple(self._callback_errors)

    def _request(self, payload: dict) -> Any:
        with self._lock:
            if self._proc is None: self.start()
            self._next_id += 1
            payload["id"] = self._next_id
            pending = queue.Queue(maxsize=1)
            self._pending[payload["id"]] = pending
            try: self._write(payload)
            except Exception:
                self._pending.pop(payload["id"], None)
                raise
        # The reader and callback handlers remain live during this wait, so
        # background observation and callbacks making nested Java calls work.
        response = pending.get()
        if "error" in response: raise BridgeError(response["error"])
        return response["result"]

    # --- public RPC operations ----------------------------------------------

    def create(self, classname: str, args: list, parameter_types=None) -> Any:
        payload = {"class": classname, "args": _encode_args(args, self)}
        if parameter_types is not None: payload["parameter_types"] = parameter_types
        result = self._request(payload)
        return _decode(self, result)

    def call(self, ref: str, method: str, args: list, parameter_types=None) -> Any:
        payload = {"ref": ref, "method": method, "args": _encode_args(args, self)}
        if parameter_types is not None: payload["parameter_types"] = parameter_types
        result = self._request(payload)
        return _decode(self, result)

    def call_static(self, classname: str, method: str, args: list, parameter_types=None) -> Any:
        payload = {"class": classname, "method": method,
                   "static": True, "args": _encode_args(args, self)}
        if parameter_types is not None: payload["parameter_types"] = parameter_types
        result = self._request(payload)
        return _decode(self, result)

    def resolve_overload(self, classname, method, candidates):
        return self._request({'class': classname, 'resolve': method, 'candidates': [
            {'parameter_types': [p['type'] for p in member['parameters']],
             'args': _encode_args(values, self)} for member, values in candidates]})

    def release(self, ref: str) -> None:
        # A dead bridge must not restart just to release a stale object.
        if self._proc is None: return
        try:
            self._request({"ref": ref, "release": True})
        except Exception:
            pass


# --- value codec -------------------------------------------------------------

_WRAPPER_TYPES = {}


def register_wrapper(java_class: str, wrapper: Type["RemoteWrapper"]) -> None:
    """Register the Python result type for an exact Java runtime class."""
    _WRAPPER_TYPES[java_class] = wrapper


class RemoteWrapper:
    """Typed facade whose RemoteObject owns the Java reference lifetime."""

    def _call(self, method: str, *args) -> Any:
        return self._remote._call(method, *args)

    def __getattr__(self, name: str):
        if name.startswith("_"):
            raise AttributeError(name)
        # Keep existing Java methods callable while explicit signatures are added.
        return getattr(self._remote, name)

    @classmethod
    def _wrap(cls, remote):
        if isinstance(remote, cls):
            return remote
        if not isinstance(remote, RemoteObject):
            raise TypeError("Expected a Java object reference")
        instance = cls.__new__(cls)
        instance._remote = remote
        return instance


class RemoteObject:
    """Opaque handle to a Java object held by the JVM bridge."""

    __slots__ = ("_bridge", "_ref", "_class", "_kind", "__weakref__")

    def __init__(self, bridge: Bridge, ref: str, java_class: str):
        self._bridge = bridge
        self._ref = ref
        self._class = java_class
        self._kind = None

    def _call(self, method: str, *args) -> Any:
        return self._bridge.call(self._ref, method, list(args))

    def __getattr__(self, name: str):
        # Dynamic method proxy: any Java method of the remote object becomes
        # callable directly (loc.getX(), rect.getWidth(), img.getSize()...).
        # Only reached for attributes NOT found through __slots__, so the
        # internal fields never collide. Dunder/underscore names are refused
        # so pickling, copying and introspection keep their normal semantics.
        if name.startswith("_"):
            raise AttributeError(name)

        def _proxy(*args) -> Any:
            return self._bridge.call(self._ref, name, list(args))

        _proxy.__name__ = name
        _proxy.__qualname__ = f"RemoteObject.{name}"
        return _proxy

    def __repr__(self) -> str:
        return f"<RemoteObject {self._class}#{self._ref}>"

    def __del__(self):
        # Best-effort GC. May fail during interpreter shutdown.
        try:
            self._bridge.release(self._ref)
        except Exception:
            pass


def _encode_args(args: list, bridge: Optional[Bridge] = None) -> list:
    return [_encode(a, bridge) for a in args]


def _encode(v: Any, bridge: Optional[Bridge] = None) -> Any:
    if isinstance(v, RemoteWrapper):
        v = v._remote
    if isinstance(v, RemoteObject):
        if bridge is not None and v._bridge is not bridge:
            raise ValueError("Cannot pass a Java object to a different JVM bridge")
        return {"__ref": v._ref}
    from ._api import JavaCallback
    if isinstance(v, JavaCallback):
        if bridge is None: raise ValueError("A callback requires a bridge")
        return bridge._encode_callback(v)
    if isinstance(v, (bytes, bytearray)):
        return [(n if n < 128 else n - 256) for n in v]
    if isinstance(v, (list, tuple)):
        return [_encode(item, bridge) for item in v]
    if isinstance(v, dict):
        if any(not isinstance(key, str) for key in v) or any(key.startswith('__') for key in v):
            return {'__map': [[_encode(key, bridge), _encode(item, bridge)] for key, item in v.items()]}
        return {key: _encode(item, bridge) for key, item in v.items()}
    return v


def _decode(bridge: Bridge, v: Any) -> Any:
    if isinstance(v, dict) and "__map" in v:
        return {_decode(bridge, k): _decode(bridge, value) for k, value in v["__map"]}
    if isinstance(v, dict) and "__ref" in v:
        ref = v["__ref"]
        cached = bridge._cache.get(ref)
        if cached is not None:
            return cached
        remote = RemoteObject(bridge, ref, v.get("__class", "?"))
        remote._kind = v.get("__kind")
        wrapper = _WRAPPER_TYPES.get(remote._class)
        if wrapper is None:
            from ._api import java_class
            parent = next((_WRAPPER_TYPES[name] for name in v.get('__types', [])
                           if name in _WRAPPER_TYPES and name != 'java.lang.Object'), None)
            wrapper = java_class(remote._class, parent=parent)
        obj = wrapper._wrap(remote)
        bridge._cache[ref] = obj
        return obj
    if isinstance(v, list):
        return [_decode(bridge, item) for item in v]
    if isinstance(v, dict):
        return {key: _decode(bridge, item) for key, item in v.items()}
    return v


# --- module-wide singleton ---------------------------------------------------

_default_bridge: Optional[Bridge] = None


def default_bridge() -> Bridge:
    global _default_bridge
    if _default_bridge is None:
        _default_bridge = Bridge()
    return _default_bridge
