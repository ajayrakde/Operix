# Python / Java argument compatibility audit

## Runtime authority

Python binds argument names and counts, converts Python callback conveniences,
and serializes values. It no longer rejects arguments based on a partial Python
copy of Java's type hierarchy. When multiple declared signatures fit the names
and argument count, the JVM scores the candidates using actual runtime classes
and Java assignability. An exact `.overload(...)` call skips that resolution.

The JVM remains responsible for primitive conversion, array elements, field
assignment and callback returns. Invalid values produce a Java-side `BridgeError`.
Ambiguous candidates report their signatures and recommend `.overload(...)`.
Multiple viable signatures require one extra local RPC before the invocation.

The bridge preserves its existing numeric conversion conventions, including
explicit-signature numeric narrowing. This is a Python-to-Java conversion
convenience; it is not a claim to reproduce javac overload resolution for every
statically typed Java expression. Python integers do not encode Java's byte,
short, int and long source types. Use `.overload(...)` when the signature matters.

## Fixed compatibility gaps

- Numbers accepted through Java `Number` and implemented interfaces.
- Inheritance and interfaces outside the inventoried Oculix packages.
- Lists accepted through their actual Java collection class and supertypes.
- Explicit varargs arrays, including `None`, byte buffers and Java array references.
- Maps preserve non-string keys; protocol-shaped keys remain ordinary map data.
- Callback return conversion checks the actual declared Java return type;
  incompatible values fail with a useful assignment error.

Cross-JVM references remain invalid because their object IDs belong to a different
process. This is a transport ownership requirement, not an additional Java type rule.

## Editor declarations

Generic metadata improves collection and iterator element hints where Java
provides concrete types. Raw types, type variables, wildcards and unspecified
external types remain `Any`. Runtime does not enforce these hints.

Reference arguments allow `None` and Java reference wrappers; primitive arguments
also allow wrappers for Java unboxing. Enum arguments retain the bridge's string
convenience. Byte arrays include Python byte buffers. Callback parameters include
Python callback forms where supported.

Nullable returns are derived from explicit source `return null` statements and
same-class return delegates. Reviewed exceptions include `Element.getLastMatch`,
`Element.getLastMatches` (their fields start null) and `Region.existsText` (its
caught search failure returns null). A field initialized to null alone does not
make every getter nullable: `Match.getTarget` repairs its field before returning.
This evidence does not establish complete nullability analysis of every method.

The typing base for known generated classes does not advertise arbitrary dynamic
attributes. External classes returned through `java_class()` remain permissive.
CI checks representative chained calls, generic results, nullable checks, valid
null arguments and unknown-method diagnostics against an installed wheel.

## Validation scope

Regression tests compare valid Java calls with RPC invocation for numeric
supertypes, interfaces, collection classes and unboxing. They exercise JVM overload
specificity, named Python binding, nested maps, varargs and invalid callback returns.
The full existing Windows/Linux desktop and OCR checks also gate release.

Method/signature coverage is complete for the pinned inventory. The regression
suite is not an exhaustive proof for every Java value and method combination.

Release 1.1.1 passed [Windows/Linux CI and publication checks](https://github.com/ajayrakde/Operix/actions/runs/36792760231).
