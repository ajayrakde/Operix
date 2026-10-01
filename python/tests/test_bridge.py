"""Integration tests for the Python wrapper.

Spawns the actual JVM bridge JAR and exchanges JSON-RPC over stdio. The
JAR is built via ``mvn package`` in ``../jvm-bridge/``.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from oculix import Location, OCR, Pattern, Region, JavaObject
from oculix._bridge import Bridge, BridgeError, RemoteObject

REPO_ROOT = Path(__file__).resolve().parents[2]
LOCAL_JAR = REPO_ROOT / "jvm-bridge" / "target" / "operix-jvm-bridge-1.2.0b1.jar"


def _java_available() -> bool:
    try:
        subprocess.run(["java", "-version"], capture_output=True, check=True)
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not LOCAL_JAR.exists() or not _java_available(),
    reason=f"Bridge JAR not built or Java missing: {LOCAL_JAR}",
)


@pytest.fixture
def bridge():
    b = Bridge(jar_path=LOCAL_JAR)
    b.start()
    yield b
    b.stop()


def test_construct_and_call_static_jdk_class(bridge):
    sb = bridge.create("java.lang.StringBuilder", [])
    assert isinstance(sb, JavaObject)
    assert sb._call("append", "hello ") is sb or sb._call("append", "hello ")._ref == sb._ref
    sb._call("append", "operix")
    assert sb._call("length") == 12
    assert sb._call("toString") == "hello operix"


def test_static_method_call(bridge):
    # java.lang.Integer.toBinaryString(42) -> "101010"
    result = bridge.call_static("java.lang.Integer", "toBinaryString", [42])
    assert result == "101010"


def test_overload_resolution(bridge):
    # Math.abs has overloads for int, long, float, double — sending an int
    # must hit Math.abs(int) and stay an int.
    assert bridge.call_static("java.lang.Math", "abs", [-7]) == 7
    # Math.max(double, double) (use doubles to disambiguate)
    assert bridge.call_static("java.lang.Math", "max", [3.5, 2.5]) == 3.5


def test_unknown_class_raises(bridge):
    with pytest.raises(BridgeError) as exc:
        bridge.create("no.such.Class", [])
    assert "ClassNotFoundException" in str(exc.value) or "no.such.Class" in str(exc.value)


def test_release_drops_ref(bridge):
    sb = bridge.create("java.lang.StringBuilder", [])
    ref = sb._ref
    bridge.release(ref)
    with pytest.raises(BridgeError):
        bridge.call(ref, "length", [])


def test_chain_returns_same_ref(bridge):
    """Identity interning: the JVM bridge should return the same ref when a
    method returns ``this`` (e.g. StringBuilder.append)."""
    sb = bridge.create("java.lang.StringBuilder", [])
    chained = sb._call("append", "x")
    assert chained._ref == sb._ref


def test_real_location_constructor_arguments_and_chain(bridge):
    location = bridge.create(Location.JAVA_CLASS, [10, 20])
    assert isinstance(location, Location)
    assert location.setX(25) is location
    assert location.getX() == 25
    copy = bridge.create(Location.JAVA_CLASS, [location])
    assert isinstance(copy, Location)
    assert copy is not location
    assert copy.getX() == 25
    assert copy.getY() == 20


def test_real_wrapper_constructor_interning(bridge, monkeypatch):
    import oculix
    monkeypatch.setattr(oculix, 'default_bridge', lambda: bridge)
    location = Location(10, 20)
    assert location.setY(30) is location
    assert location.getY() == 30


def test_real_pattern_chain(bridge):
    pattern = bridge.create(Pattern.JAVA_CLASS, ['button.png'])
    assert isinstance(pattern, Pattern)
    assert pattern.similar(0.7) is pattern
    assert pattern.getSimilar() == pytest.approx(0.7)


def test_real_ocr_options_clone_and_chaining(bridge):
    options = bridge.create(OCR.Options.JAVA_CLASS, [])
    assert isinstance(options, OCR.Options)
    assert options.language('hin') is options
    clone = options.clone()
    assert isinstance(clone, OCR.Options)
    assert clone is not options
    assert clone.language() == 'hin'
    assert clone.language('eng') is clone
    assert options.language() == 'hin'


def test_real_global_ocr_options_static_factory(bridge, monkeypatch):
    import oculix
    monkeypatch.setattr(oculix, 'default_bridge', lambda: bridge)
    options = OCR.globalOptions()
    assert isinstance(options, OCR.Options)
    assert OCR.globalOptions() is options


@pytest.mark.skipif(os.environ.get('OCULIX_DESKTOP_TESTS') != '1', reason='Requires a real graphical desktop; set OCULIX_DESKTOP_TESTS=1')
def test_real_virtual_region_result_and_reference_argument(bridge):
    rectangle = bridge.create('java.awt.Rectangle', [10, 20, 30, 40])
    region = bridge.call_static(Region.JAVA_CLASS, 'virtual', [rectangle])
    assert isinstance(region, Region)
    assert region.getX() == 10
    assert region.getY() == 20
    assert region.getW() == 30
    assert region.getH() == 40


def test_invoked_java_error_exposes_cause(bridge):
    with pytest.raises(BridgeError, match='NumberFormatException'):
        bridge.call_static('java.lang.Integer', 'parseInt', ['not-an-integer'])


@pytest.mark.skipif(os.environ.get('OCULIX_OCR_TESTS') != '1', reason='Opt-in native OCR smoke test; set OCULIX_OCR_TESTS=1')
@pytest.mark.parametrize("with_options", [False, True])
def test_real_ocr_image_read(bridge, with_options):
    options = bridge.create(OCR.Options.JAVA_CLASS, [])
    options.language('eng').psm(7)
    image = str(Path(__file__).parent / 'fixtures/ocr-submit.png')
    args = [image, options] if with_options else [image]
    text = bridge.call_static(OCR.JAVA_CLASS, 'readText', args)
    assert 'Submit 12345' in text
    # Ensure this is the bundled engine, even with system Tesseract installed.
    if bridge.call_static('java.lang.System', 'getProperty', ['os.name']) == 'Linux':
        library = bridge.call_static('com.sun.jna.NativeLibrary', 'getInstance', ['tesseract'])
        loaded_path = library._call('getFile')._call('getAbsolutePath')
        assert '/operix/ocr-oculix-4.0.0/' in loaded_path
        assert loaded_path.endswith('/libtesseract.so')


def test_arrays_collections_nested_references_and_char(bridge):
    assert bridge.call_static('java.util.Arrays', 'toString', [[1, 2, 3]], parameter_types=['int[]']) == '[1, 2, 3]'
    assert bridge.call_static('java.util.Collections', 'singletonList', [{'nested': [1, 2]}]) == [{'nested': [1, 2]}]
    assert bridge.call_static('java.util.Collections', 'singletonMap', [3, 'three']) == {3: 'three'}
    location = bridge.create(Location.JAVA_CLASS, [7, 8])
    assert bridge.call_static('java.util.Collections', 'singletonList', [location]) == [location]
    assert bridge.call_static('java.lang.Character', 'toUpperCase', ['a'], parameter_types=['char']) == 'A'
    assert bridge.call_static('java.util.Arrays', 'asList', ['one', 'two'], parameter_types=['java.lang.Object[]']) == ['one', 'two']


def test_exact_overload_enum_keywords_and_fields(bridge, monkeypatch):
    import oculix
    monkeypatch.setattr(oculix, 'default_bridge', lambda: bridge)
    location = Location(x=0, y=20)
    assert location.getX() == 0
    location.x = 15
    assert location.x == 15
    options = OCR.Options()
    enum = OCR.PSM.SINGLE_LINE
    assert isinstance(enum, OCR.PSM)
    assert enum.name() == 'SINGLE_LINE'
    assert options.psm(enum).psm() == 7
    assert options.psm.overload('org.sikuli.script.OCR$PSM')('SINGLE_LINE').psm() == 7
    original = oculix.Settings.MoveMouseDelay
    try:
        oculix.Settings.MoveMouseDelay = 0.25
        assert oculix.Settings.MoveMouseDelay == pytest.approx(0.25)
    finally:
        oculix.Settings.MoveMouseDelay = original


def test_callbacks_can_make_nested_java_calls(bridge):
    from oculix import JavaCallback
    seen = []
    def compare(a, b):
        seen.append((a, b))
        return bridge.call_static('java.lang.Integer', 'compare', [a, b])
    stream = bridge.call_static('java.util.Arrays', 'stream', [[3, 1, 2]], parameter_types=['java.lang.Object[]'])
    comparator = JavaCallback('java.util.Comparator', compare)
    ordered = bridge.call(stream._ref, 'sorted', [comparator], parameter_types=['java.util.Comparator'])
    assert ordered._call('toArray') == [1, 2, 3]
    assert seen
    assert bridge.callback_errors == ()


def test_iterator_result_is_python_iterable(bridge):
    stream = bridge.call_static('java.util.Arrays', 'stream', [[3, 1, 2]], parameter_types=['java.lang.Object[]'])
    assert list(stream._call('iterator')) == [3, 1, 2]


def test_named_binding_uses_jvm_inheritance_and_collection_types(bridge, monkeypatch):
    import oculix
    from oculix._api import JavaMeta, JavaObject, JavaMethod
    monkeypatch.setattr(oculix, 'default_bridge', lambda: bridge)

    # Exercise the exact generated binding path against public JDK signatures.
    def facade(name, method, signatures):
        members = [{'name': method, 'static': True, 'varargs': False,
                    'parameters': [{'name': 'arg' + str(i), 'type': typ} for i, typ in enumerate(types)]}
                   for types in signatures]
        return JavaMeta('TestFacade', (JavaObject,), {'JAVA_CLASS': name, method: JavaMethod(method, members)})

    numbers = facade('java.lang.String', 'valueOf', [['java.lang.Object'], ['int'], ['double']])
    assert numbers.valueOf(3) == '3'
    assert numbers.valueOf(3.5) == '3.5'
    assert numbers.valueOf(None) == 'null'
    failure = oculix.FindFailed("missing")
    # Known Oculix objects remain valid for Java reference signatures.
    assert numbers.valueOf(failure) == failure.toString()
    collections = facade('java.util.Collections', 'max', [['java.util.Collection']])
    assert collections.max([1, 3, 2]) == 3
    stream = bridge.call_static('java.util.Arrays', 'stream', [[3, 1, 2]], parameter_types=['java.lang.Object[]'])
    assert list(stream._call('iterator')) == [3, 1, 2]


def test_named_varargs_accept_null_array_and_remote_array(bridge, monkeypatch):
    import oculix
    from oculix._api import JavaMeta, JavaObject, JavaMethod
    monkeypatch.setattr(oculix, 'default_bridge', lambda: bridge)
    member = {'name': 'format', 'static': True, 'varargs': True,
              'parameters': [{'name': 'format', 'type': 'java.lang.String'},
                             {'name': 'args', 'type': 'java.lang.Object[]'}]}
    strings = JavaMeta('Strings', (JavaObject,), {'JAVA_CLASS': 'java.lang.String', 'format': JavaMethod('format', [member])})
    assert strings.format('%s %s', None) == 'null null'
    assert strings.format('%s %s', ['one', 'two']) == 'one two'
    assert strings.format('%s %s', 'one', 'two') == 'one two'
    assert strings.format('%s', args=['one']) == 'one'
    failure = oculix.FindFailed('missing')
    assert strings.format('%s', failure) == failure.toString()


def test_input_maps_preserve_non_string_keys_and_reserved_names(bridge):
    value = {3: 'three', '__map': 'ordinary data', 'nested': {7: [1, 2]}}
    assert bridge.call_static('java.util.Collections', 'singletonList', [value]) == [value]


def test_callback_return_is_checked_against_java_signature(bridge):
    from oculix import JavaCallback
    stream = bridge.call_static('java.util.Arrays', 'stream', [[1]], parameter_types=['java.lang.Object[]'])
    predicate = JavaCallback('java.util.function.Predicate', lambda value: 'not a boolean')
    filtered = bridge.call(stream._ref, 'filter', [predicate], parameter_types=['java.util.function.Predicate'])
    with pytest.raises(BridgeError, match='Cannot assign java.lang.String to boolean'):
        filtered._call('count')
