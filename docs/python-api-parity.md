# Python / Oculix Java API parity

Target: Oculix **4.0.0**, pinned by `jvm-bridge/pom.xml`.
Fork distribution: **oculix-operix 1.1.0**; Python imports remain `oculix`.

## Implemented API

- All 211 inventoried public Java types have registered, named Python facades.
- All 13,574 public method overload occurrences (including inheritance, excluding
  Object methods in the coverage count) have exact Java signature metadata. The
  inventory contains 3,168 distinct method definitions. No method overloads are
  missing from the generated surface.
- All public constructors and fields are exposed. Static/instance placement,
  public inheritance, nested types, enum constants, parameter types and varargs
  are preserved. Unsupported older declarations were removed.
- Generated `.pyi` declarations provide named arguments, overloads, return hints
  and editor completion. The runtime binds against the same finite declaration
  set rather than accepting arbitrary Oculix method names.
- Published source declarations supplement binary parameter metadata. Fourteen
  VNC declarations lack parameter names in the available source artifact and
  preserve the binary names `arg0`, etc.; every argument and type is still present.
  Java/Python reserved words get a trailing underscore, e.g. `Debug.is_`.
- Exact signature requests resolve overloads in Java. For ambiguous null/reference
  values, use `method.overload('java.type.Name', ...)(arguments)`.
- Returned references preserve identity and typed wrappers; the raw RemoteObject
  is an internal lifetime owner. External Java types receive named facades.
- Python lists/tuples, dictionaries, primitive arrays, char, enums, collections,
  nested references, varargs and Java iterators are supported. Collections/arrays
  return Python sequences and maps return Python dictionaries. Cycles fall back
  to Java references instead of recursing indefinitely.
- Public static/instance fields read and write the actual Java field without a
  stale constants cache; final fields reject assignment.
- Java interface callbacks use `JavaCallback(interface, handler)`. Oculix observer
  callbacks also accept Python functions or `JavaCallback(ObserverCallBack, handler)`.
  The protocol supports background callbacks and callbacks making nested Java
  calls; Python callback errors are available through `Bridge.callback_errors`.

## Validation

The local JVM/transport suite passes 50 tests, including exact overloads, typed
identity, nested maps/arrays, enum and field access, iterator access and a callback
that performs nested Java calls. Eleven Java dispatcher/server tests pass.

Native image OCR passes with and without options on Linux and Windows Server 2025
x64 using Java 17 / Python 3.12. Linux explicitly binds the bundled matching
Tesseract/Leptonica pair; it verifies the loaded file and version rather than using
an older system Tesseract. Cold and warm native-cache checks pass locally.

CI additionally validates a real Swing desktop: capture, OCR text search, image
search, click, keyboard input, clipboard paste and background observation. These
checks require a graphical session; Linux CI uses Xvfb. Check the latest workflow
run for the result of those desktop tests. VNC/ADB/SSH endpoints, every OCR language
and macOS have not been separately exercised; declaration coverage does not mean
that every Java method has a runtime test.

The wheel and sdist build and pass package metadata checks. A clean wheel install
outside the checkout loads the full generated API and reads the OCR fixture via
its built JVM bridge. Release validation also checks automatic JAR download from
this fork. PyPI publication requires publishing access for `oculix-operix`.

## Reproduce

```sh
cd jvm-bridge
mvn -B package
cd ..
python -m pip install -e ./python pytest build twine
OCULIX_OCR_TESTS=1 python -m pytest python/tests -q
python tools/inventory_java_api.py --check
python tools/generate_python_api.py --check
python -m build python
python -m twine check python/dist/*
python tools/verify_python_wheel.py
```

Set `OCULIX_DESKTOP_TESTS=1` and run `python/tests/test_desktop.py` on a graphical
session. The source fixture is compiled into `jvm-bridge/target/test-classes`.
Java 17+ is used for builds and inventory tooling. A JRE containing the compiler
module can also compile helpers through Eclipse ECJ with `--compiler-jar`.

## Generation and coverage

[Coverage report](python-api-coverage.md) compares every exact generated overload
with the binary inventory. [Machine inventory](java-api-4.0.0.json.gz) preserves
constructors, fields, exception types and generic types.

`tools/java/SourceParameters.java` parses the published sources with javac's AST
without dependency resolution. Its compressed output is committed as
`tools/java-source-parameters.json.gz`. `tools/generate_python_api.py` combines
source names with the binary inventory to generate the packaged runtime schema
and complete overload stubs. CI fails if either generated artifact is stale.
