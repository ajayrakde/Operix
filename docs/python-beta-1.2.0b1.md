> Historical release notes for oculix-operix 1.2.0b1, before the Pyulix rename.

# Typed support beta: oculix-operix 1.2.0b1

Install explicitly:

```sh
python -m pip install --upgrade oculix-operix==1.2.0b1
```

This is a PyPI prerelease and GitHub prerelease. Stable 1.1.1 remains available.
The Python import remains `oculix`.

All 126 audited signatures in core desktop/images/OCR support, utilities/files,
GUI overlays, guide annotations, and desktop devices now have named return
types. 123 use public Java facades; three return typed opaque handles.
The bounded support inventory has 16 root types and 11 public superclasses;
the original Oculix API inventory remains separate.

```python
from oculix import BufferedImage, Image, Pattern, OCR

pixels = BufferedImage(100, 50, BufferedImage.TYPE_INT_RGB)
graphics = pixels.createGraphics()
try:
    graphics.fillRect(0, 0, 100, 50)
finally:
    graphics.dispose()

pattern = Pattern(pixels)  # Same Java reference goes back to Java.
loaded = Image.create('screen.png').get()
if loaded is not None:
    print(OCR.readText(loaded))
```

Java runtime subclasses retain a compatible facade and their actual identity.
Graphics implementations are invoked through the exported public Java API.
The established `Image` alias remains Oculix Image; AWT Image is `JavaImage`.

`Pattern.overload('java.lang.String')(None)` selects an exact constructor and
preserves Java's supported invalid-image behavior. Bare ambiguous calls still
require caller intent. Bound method `.overload` works at runtime, but its
function-attribute typing limitation remains.

Reviewed invalid-null arguments now raise TypeError identifying the method and
parameter. This covers selected Image/Pattern constructors and methods,
Region.create reference arguments, OCR.Options.psm(enum), and the options
argument of OCR.readText. Omit readText options to use global defaults, or pass
an Options object. OCR.readLines(source, None) still uses global defaults.
This guards known failures; it does not guarantee that all Java internals avoid
NullPointerException.

NewAnimator and SXDialog.BasicItem are opaque, non-constructible types. Return
values can be passed back to public owner APIs. Direct implementation member
access raises AttributeError; supported public operations include
Visual.addAnimation and SXDialog.getText/setText. Java must expose a public
interface before those implementation members become direct supported APIs.

Object/type-variable values and types outside the bounded inventory remain
permissive. Facade generation does not add a blanket Python runtime type gate.
Nullable results require a check before chaining. Resources still require
explicit close/dispose/release. Generic GUI thread routing, modal cancellation,
multi-monitor behavior, and complete animation playback are not newly guaranteed.
