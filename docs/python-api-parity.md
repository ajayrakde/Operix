# Python / Oculix Java API parity

Target: the Oculix **4.0.0** API currently pinned by `jvm-bridge/pom.xml`.
The goal is the public Java API as-is: names, arguments, overloads, constructors,
static methods, return types, inheritance and OCR. `_call` stays an internal
implementation detail. Dynamic forwarding is an interim compatibility fallback,
not a substitute for explicit signatures and autocomplete.

## First implementation

- Registered Java runtime classes decode into typed Python wrappers.
- `Match` keeps its `Region` inheritance.
- Constructors, static factories and returned `this` references share identity.
- A single underlying `RemoteObject` owns reference release, preventing a temporary
  wrapper or a deleted alias from invalidating a live Java object.
- Wrapper arguments are encoded as their Java references; passing objects between
  JVM bridges raises an error before sending a request.
- Core result types now include `Location`, `Image` and `ScreenImage`.
- OCR result types include `OCR.Options`, `PaddleOCRClient` and `TesseractEngine`.
- `Region.findText(text)` is explicit. `OCR.readText(target, options)` supports
  both Java overloads, including explicitly supplied null options.
- `Region.exists()` returns `Match` or `None`, replacing the previous Boolean
  conversion. Existing truth checks still work; `is True` checks must change.

## Remaining work

1. Use the committed Java inventory and coverage report to drive implementation.
   Supplement missing source parameter names where the JAR lacks name metadata.
2. Generate explicit Python signatures and overload type hints, with every Java
   parameter preserved. Remove Python defaults that change Java overload behavior.
3. Expand runtime-class registration, including Java subclasses and enum types.
4. Support Java arrays, collections, iterators, enums, varargs and callbacks through
   the JVM bridge, with tests for overloaded calls and nested references.
5. Complete OCR options, engines, text search and results. Match actual Java
   signatures rather than older example documentation.
6. Finish actual desktop and native OCR validation. The headless JVM tests and
   reproducible API coverage check are now in place.

The recursive Python codec does not yet convert JSON containers into Java
collections or arrays. Unknown Java classes still use the generic proxy.
The implementation establishes typed core objects and validates them against Java;
it does not claim complete API parity or successful desktop/native OCR validation.

## Tests

```sh
PYTHONPATH=python/src python -m pytest python/tests -q
```

Transport-level tests use recorded JSON requests and test typed dispatch, ownership,
GC, argument conversion and result identity without a desktop. JVM integration tests
require Java and `jvm-bridge/target/operix-jvm-bridge-1.0.0.jar`; build with Maven first.

## JVM validation and API inventory

- 41 Python tests pass, including 12 actual JVM integration tests.
- 11 Java dispatcher/server tests pass.
- Desktop and native OCR tests are explicit opt-in checks (2 skipped by default).
- 211 public Java types and 3,168 distinct public method definitions were reflected
  without initializing classes; no classes were unavailable. Per-class inventories
  preserve inherited overloads and public constructors/fields.
- [Coverage report](python-api-coverage.md) distinguishes explicit names and arities
  from semantic parity. Dynamic forwarding does not count as explicit coverage.
- [Compressed machine manifest](java-api-4.0.0.json.gz) contains complete type and
  overload metadata. Decompress with Python's `gzip` module to inspect it.
- Reflection errors now expose the invoked Java exception rather than just
  `InvocationTargetException`. This improvement requires building the fork's bridge;
  the upstream released 1.0.0 JAR still has the old error behavior.

The native OCR smoke test was attempted and failed on this Linux runtime. Direct
Java execution confirms JNA selects the system Tesseract 5.0.3 library, missing
`TessBaseAPIGetPAGEText`. Typed OCR options and argument conversion pass; image-text
recognition remains blocked by native library loading. No Windows OCR claim is made.

The `Region.virtual()` check was also attempted and rejected by Oculix in the
headless runtime. A real graphical desktop is required for that test.

Rebuild and reproduce:

```sh
cd jvm-bridge
mvn -B package
cd ..
python -m pip install -e ./python pytest
python -m pytest python/tests -q
python tools/inventory_java_api.py --check
```

Regenerate coverage after wrapper changes:

```sh
python tools/inventory_java_api.py
```

Java 17+ JDK is required for inventory generation. `--compiler-jar /path/to/ecj.jar`
is an alternative for a JRE-only environment using Eclipse's Java compiler.

Opt-in runtime checks (fail on errors rather than hiding them):

```sh
OCULIX_OCR_TESTS=1 python -m pytest python/tests/test_bridge.py -k real_ocr_image_read -q
OCULIX_DESKTOP_TESTS=1 python -m pytest python/tests/test_bridge.py -k virtual_region -q
```
