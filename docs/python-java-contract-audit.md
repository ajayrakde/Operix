# Concrete Java contracts: overloads, null, and Any

Audit date: 2026-10-01. Bridge: pyulix 1.1.1. Java dependency:
`io.github.oculix-org:oculixapi:4.0.0`.

Evidence is the [published Java sources](https://repo.maven.apache.org/maven2/io/github/oculix-org/oculixapi/4.0.0/oculixapi-4.0.0-sources.jar)
and 21 real calls against `operix-jvm-bridge-1.1.1.jar`. These are targeted
checks, not exhaustive testing of every signature or desktop state. No runtime
behavior has been changed by this audit.

## Verified calls

In the table, “exact” means selecting the indicated Java signature, rather than
asking the dispatcher to infer a signature from None.

| Call | Observed Java behavior | Appropriate handling |
| --- | --- | --- |
| `Image.create(None)` | Ambiguous between File, String, URL, Image, Pattern | Require caller intent; do not select arbitrarily. |
| `Image.create` exact String, None | Returns Image; `isValid()` is false | Preserve supported behavior. Null does not mean a valid image. |
| `Image.create` exact URL, None | NPE in downstream filename-extension validation | A Python guard can give a useful error; Java needs a fix if null should produce an empty image here. |
| `Image.create` exact File, None | NPE calling `imageFile.getAbsolutePath()` | Guard this exact parameter before entering Java. |
| `Image.create` exact Image, None | NPE calling `imgSrc.copy()` | Guard this exact parameter. |
| `Image.create` exact Pattern, None | NPE calling `p.getImage()` | Guard this exact parameter. |
| `OCR.Options.language(None)` | IllegalArgumentException: invalid language null | Java already validates; expose clearly. Do not substitute a language silently. |
| `OCR.Options.psm(None)` | Chooses enum signature, then NPE calling `ordinal()` | Guard null for PSM enum. |
| `OCR.Options.psm` exact int, None | Dispatcher rejects null for primitive int | Already handled before invoking the Java method. |
| `OCR.readText(fixture, None)` | NPE calling `options.psm()` | Guard options, or make a documented Python convenience use global options; Java fix needed for consistent null-default semantics. |
| `OCR.readLines(fixture, None)` | Successfully returns a list | Preserve: TextRecognizer.get substitutes global options. |
| `OCR.readText(None)` | IllegalArgumentException: null | Source is required; Java already rejects it. |
| `Pattern(None)` | Ambiguous between six reference constructors | Caller must identify the constructor. Current error incorrectly recommends a class-level `.overload` helper that is absent. |
| `Pattern` exact String, None | Constructs; `isValid()` is false | Preserve supported behavior. |
| `Pattern` exact URL, None | SikuliXception: FATAL, resource URL null | Java deliberately rejects missing resources. It throws; this path does not exit the JVM. |
| `Pattern` exact BufferedImage, None | NPE calling image width | Guard this exact parameter. |
| `Pattern` exact Image, None | NPE in Image.copy | Guard this exact parameter. |
| `Pattern` exact Pattern, None | NPE reading source pattern | Guard this exact parameter. |
| `Pattern` exact ScreenImage, None | NPE calling getImage | Guard this exact parameter. |
| `Pattern().targetOffset(None)` | NPE reading Location.x | Guard Location argument. |

The remaining verified call was `isValid()` on the null-String Image.
OCR fixture: `python/tests/fixtures/ocr-submit.png`.

Earlier discussion incorrectly described `OCR.readText(source, None)` as using
default options. The actual method accesses `options.psm()` before reaching
TextRecognizer.get, so its behavior differs from readLines.

## Additional source-backed cases (not desktop runtime tests)

* `Region.create(Location, int, int)` reads loc.x and loc.y immediately;
  `Region.create(Rectangle)` and `Region.create(Region)` also dereference the
  supplied argument. Null guards are appropriate for those signatures.
* `Element.getImageFromTarget` accepts String, Pattern, Image, or ScreenImage;
  every other value, including null, throws IllegalArgumentException. Its
  unbounded Java type variable is more permissive than its implementation.
* OCR source conversion in `Element.getBufferedImage` accepts String, File,
  Match, Region, Image, ScreenImage, and BufferedImage. Null and unsupported
  objects are explicitly rejected. Match is covered by Region's inheritance,
  but is handled specially in the implementation.
* `ObserveEvent.setRegion(Object)` ignores non-Region values, including null.
  `setMatch(Object)` ignores non-Match values and null; `setChanges(List)`
  ignores null. Rejecting every such input would change Java behavior.
* `ObserveEvent.setImage(Object)` casts to Image: null is accepted and clears
  the field; an incompatible object produces ClassCastException.
* `Match.getTarget()` returns its target or falls back to its center. A null
  internal target does not make this return nullable.
* `Element.getLastMatch()` / `getLastMatches()` can return null before a
  search; Region.exists returns null for an unsuccessful search. Represent
  these as optional results and require callers to check before chaining.

## What can be fixed in Python

1. Type the existing bound-method `.overload(*types)` helper so editors support
   exact selection. Add an equivalent constructor selector and correct the
   current constructor ambiguity message. Low-level `Bridge.create` already
   supports exact parameter types.
2. Keep JVM assignability and most-specific overload selection. Add narrowly
   reviewed non-null contracts for signatures that demonstrably dereference
   null; report method, parameter, and expected type before crossing the JVM.
   Do not infer non-null from reference type alone.
3. Generate facades for known external Java types. `ScreenImage.getImage()`
   and `Image.get()` declare BufferedImage; Image.create declares File and URL
   inputs. Their Any hints are bridge coverage gaps, not missing Java types.
4. Add semantic aliases for OCR sources and image-search targets, backed by
   the actual source branches. Because Java generics permit arbitrary objects
   at compile time, retain a permissive compatibility route rather than
   imposing new blanket runtime restrictions.

## Oculix-declared return typing gaps by area

The [scoped return inventory](python-any-return-audit-4.0.0.csv) contains
**152 public method signatures declared by Oculix's inventoried public types**
whose return types are known in Java but currently have plain `Any` Python
hints. Rows are grouped by the new `Area` column and sorted by method signature.

Inherited methods declared by Java and third-party types are outside this audit
scope. They remain accessible through Oculix public types and can still matter
to Python consumers who use them; this exclusion does not remove or change
bridge support. External return types of Oculix-declared methods remain in
scope: for example, BufferedImage, File, URL, and native handles.

| Area | Distinct public method signatures |
| --- | ---: |
| Android | 9 |
| Command execution and runners | 4 |
| Common utilities and file management | 43 |
| Core desktop and images / OCR support | 43 |
| Desktop devices | 11 |
| GUI dialogs and capture overlays | 16 |
| Guide and visual annotations | 13 |
| Native platform integration | 5 |
| Preferences | 3 |
| VNC | 5 |
| **Total** | **152** |

Grouping follows the declaring class and functional area, not the return type.
Core desktop includes org.sikuli.script and TesseractLastSeen; desktop devices
covers org.sikuli.support.devices. Guide covers org.sikuli.guide; GUI dialogs
and capture overlays covers org.sikuli.support.gui and org.sikuli.util.
Common utilities/file management covers Commons and FileManager. The latter
are publicly accessible support APIs, not all everyday automation methods.

Methods are deduplicated by declaring class and parameter signature; overloads
are separate signatures. This CSV excludes plain Object/type-variable returns,
Any in inputs, and nested generic containers. Those separate limitations and
the source-backed null/overload findings above remain part of this report.

## Resolution plan for the five selected areas

The selected areas total **126 signatures**. Of these, **123** return one of
**16 public Java types** and can gain concrete reference facades. The remaining
**3** return two non-public Oculix implementation types and need opaque handles
or a public Java API. The CSV now records proposed handling on each row.

| Public return type | Signatures across these areas |
| --- | ---: |
| java.io.File | 36 |
| java.net.URL | 25 |
| java.awt.image.BufferedImage | 22 |
| java.awt.Rectangle | 11 |
| java.awt.Point | 10 |
| org.opencv.core.Mat | 5 |
| java.awt.Dimension | 3 |
| java.awt.Color | 3 |
| java.io.BufferedReader | 1 |
| java.lang.Class | 1 |
| java.net.Proxy | 1 |
| java.net.InetAddress | 1 |
| java.awt.Robot | 1 |
| javax.swing.JPanel | 1 |
| java.awt.Graphics2D | 1 |
| java.awt.Insets | 1 |
| **Public-type total** | **123** |

### Preserve Java reference semantics

Add explicitly selected dependency types to the schema and generated stubs,
separately from the Oculix-owned audit inventory. Include needed public
supertypes/interfaces, constructors, fields, signatures, and argument metadata.
Use the existing reference registry, overload dispatch, and actual JVM
assignability; do not replace File with pathlib.Path, URL with str,
BufferedImage with Pillow images, or Mat with NumPy arrays automatically.
Such conversions lose identity, may change behavior, and prevent passing the
same reference back to Java. Optional explicit converters can be added later.

Returned objects may have a runtime subclass different from the declared return
type (especially JPanel/Graphics2D and Class implementations). A declaration in
a stub alone is insufficient: decoding must select a compatible typed facade
for those objects and preserve callable runtime public methods. Audit direct
and inherited methods on the support facades for dependent types. Do not
recursively inventory every reachable JDK class without a bounded scope.

Nullability needs its own per-signature review. For example, Image.getURL and
Image.file can return null; Image.getLastSeen is null before a successful find;
SXDialog.getItem can return null when a reference name is missing; file chooser
cancellation returns null. Do not change all Any returns to non-optional types.

### Work by area

* **Core desktop/images/OCR support (43):** begin with File, URL,
  BufferedImage, Rectangle, Point, Dimension, Color, BufferedReader and Mat.
  Verify image dimensions/pixels, crop/resize, path lookup, reader close,
  nullable image metadata, and passing BufferedImage back to Pattern/OCR.
  Apply the separately documented OCR argument contracts; typing these return
  values alone does not fix OCR options-null behavior.
* **Common utilities/files (43):** reuse image/path/Mat types and add Class,
  Proxy and InetAddress. Verify temporary files, URL/File round trips,
  image/Mat conversion and explicit release/close. Cleanup must operate only
  on test-owned files. Generic Class metadata may remain open-ended even
  after the Class object itself has a concrete facade.
* **GUI dialogs/capture overlays (16):** reuse geometry, File and BufferedImage;
  add JPanel and Graphics2D. Check dialog cancellation, missing item names,
  drawing/dispose and capture selection on Windows/Linux desktop fixtures.
  Review Swing/AWT thread requirements before claiming these calls are safe
  on the bridge's RPC thread. Native dialogs, focus and display availability
  require actual desktop validation.
* **Guide/annotations (13):** add Insets and reuse geometry/images. Check
  inherited component geometry, placement, image rendering, animation queueing
  and completion using desktop fixtures; keep non-public animator objects as
  opaque handles until there is a supported public Java interface.
* **Desktop devices (11):** add Robot and reuse geometry/colors/images. Verify
  capture dimensions, colors, movement and passing returned references back
  to Java. Use existing Windows/Linux CI desktop jobs; multi-monitor behavior
  needs a fixture with multiple displays before it can be claimed verified.

### Non-public return types: actual access limitation

`AnimationFactory.createCircleAnimation` and `createOpacityAnimation` return
package-private `NewAnimator`; `SXDialog.getItem` returns package-private
`SXDialog.BasicItem`. These are three public method signatures, but their
return types are not public consumer APIs.

Real JVM checks on 2026-10-01 confirmed:

* Visual.getBounds/getLocation/getPreferredSize are inherited methods and
  successfully return Rectangle/Point/Dimension reference objects.
* createCircleAnimation returns a CircleAnimator reference; passing it to
  Visual.addAnimation succeeds.
* Calling setLooping on the returned animator fails with IllegalAccessException:
  Dispatcher cannot access the public member declared on non-public NewAnimator.

Represent animator/item references as named opaque types for safe passing and
optional results. Use public Visual animation helpers and SXDialog.getText /
setText for supported operations. A Java public interface or public wrapper is
the clean solution for direct animator/item operations. Broad setAccessible
changes would bypass Java access boundaries and are not part of this plan.

### Why inherited methods can still be called directly

Examples present in the actual inventory include SxImage.getBounds/getLocation
(declared on java.awt.Component), RobotDesktop.createScreenCapture(Rectangle)
(declared on java.awt.Robot), and OverlayTransparentWindow.getContentPane
(declared on javax.swing.JFrame). They are ordinary method calls on Oculix
objects. Their exclusion from the Oculix-owned gap CSV is a reporting boundary;
they should remain callable and share the newly added support types.

### Implementation and evidence order

1. Add the support-type inventory/facades with compatible decoding; verify
   constructors, fields, inheritance, subtype returns and JVM round trips.
2. Regenerate Oculix return/input hints and add reviewed nullable contracts;
   verify editor inference, bad-method diagnostics and reference pass-back.
3. Cover core images/OCR/files first, then desktop devices and GUI/guide jobs.
4. Track opaque Java return types separately; Java interface changes are needed
   only for direct operations on their inaccessible implementation APIs.

Implemented in **1.2.0b2**: 27 public support facades (16 roots plus their
public superclasses), two opaque types, runtime subtype metadata, invocation
through exported Java APIs, reviewed nullable results and invalid-null guards,
and exact constructor selection via Class.overload. The CSV records actual beta
return hints for all 126 selected signatures. Generic Object values remain Any.
Local validation passed 62 Python checks and 15 Java checks; Windows/Linux
desktop validation and publication run through the gated release workflow.
Modal cancellation, full animation playback, multi-monitor behavior, and every
GUI method/argument combination are not covered by these checks.

## What requires caller information or a Java change

* A bare None cannot identify one of unrelated reference overloads. Python
  overload declarations describe alternatives to a type checker; they do not
  add runtime intent. Exact selection or a typed null wrapper can supply it.
* Python int/float values do not encode every Java primitive width. A natural
  default is possible, but exact overload selection remains necessary when
  Java int versus long or float versus double affects behavior. Existing
  numeric narrowing must be considered separately from overload selection.
* `ObserveEvent.getVals()` returns Object[]. Its own Java documentation says
  the three values follow a private protocol shared by creator and consumer.
  No single more specific element type can be inferred safely. A user-supplied
  typed adapter can check that private protocol; generic event values remain
  open-ended.
* Null handling inside Java, such as the OCR options inconsistency and URL
  image validation, requires a Java fix to make Java callers safe too.
  A bridge guard can prevent these identified NPEs from Python but cannot
  guarantee that every internal Java operation avoids NPE.

Source files examined: org/sikuli/script/{Image,Pattern,OCR,TextRecognizer,
Element,Region,Match,ObserveEvent}.java and org/sikuli/support/Commons.java.
