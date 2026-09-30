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

1. Inventory public methods and overloads from the pinned JAR, including inherited
   methods and nested OCR types. Keep an API coverage manifest in the repository.
2. Generate explicit Python signatures and overload type hints, with every Java
   parameter preserved. Remove Python defaults that change Java overload behavior.
3. Expand runtime-class registration, including Java subclasses and enum types.
4. Support Java arrays, collections, iterators, enums, varargs and callbacks through
   the JVM bridge, with tests for overloaded calls and nested references.
5. Complete OCR options, engines, text search and results. Match actual Java
   signatures rather than older example documentation.
6. Run JVM integration and actual screen/OCR tests, then automate API coverage checks
   so future Java releases expose changes rather than silently losing methods.

The recursive Python codec does not yet convert JSON containers into Java
collections or arrays. Unknown Java classes still use the generic proxy.
The first implementation therefore establishes typed core objects; it does not
claim complete API parity or desktop/OCR execution validation.

## Tests

```sh
PYTHONPATH=python/src python -m pytest python/tests -q
```

Transport-level tests use recorded JSON requests and test typed dispatch, ownership,
GC, argument conversion and result identity without a desktop. JVM integration tests
require Java and `jvm-bridge/target/operix-jvm-bridge-1.0.0.jar`; build with Maven first.
