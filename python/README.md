> **Independent fork:** Pyulix is maintained by **Ajay Rakde** and is neither affiliated with nor endorsed by the OculiX project. Original work by Julien Mer and contributors; original copyright and MIT license notices are preserved. [Support](https://github.com/ajayrakde/Operix/issues).

# Pyulix (Python)

![Pyulix](https://raw.githubusercontent.com/ajayrakde/Operix/rebrand/pyulix/docs/branding/pyulix-logo.png)

Python wrapper for [OculiX](https://github.com/oculix-org/Oculix) — visual automation for the real world.

## Install

```bash
pip install --pre pyulix
```

Requirements: Python 3.8+, Java 17+ on `PATH` (Eclipse Temurin or Azul Zulu).

The OculiX engine (~200 MB fat JAR) is downloaded on first use into `~/.pyulix/lib/`.

## Quickstart

```python
from pyulix import Screen, App, VNCScreen

screen = Screen()
screen.click("login.png")
screen.type("admin")
screen.click("submit.png")
screen.wait("dashboard.png", 10)

# Open a desktop app
calc = App.open("calc")
screen.click("button_7.png")

# Drive a remote VNC display
vnc = VNCScreen.start("10.0.0.42", 5900, "", 1920, 1080)
vnc.click("logo.png")
vnc.stop()
```

## With pytest

```python
import pytest
from pyulix import Screen, App

@pytest.fixture
def calc():
    a = App.open("calculator")
    yield a
    a.close()

def test_addition(calc):
    s = Screen()
    s.click("button_7.png")
    s.click("button_plus.png")
    s.click("button_3.png")
    s.click("button_equals.png")
    assert s.exists("result_10.png")
```

## License

MIT

## Java API parity

This fork exposes the complete pinned Oculix 4.0.0 public method surface: 211
public types with named Python methods, constructor/field access and every Java
overload's arguments. `from pyulix import Screen, OCR, Pattern` uses the new independent namespace.
Every class is also available through `pyulix.java`; nested classes keep names
such as `OCR.Options` and `OCR.PSM`.

```python
from pyulix import Screen, Pattern, Match, OCR, Location, JavaCallback, ObserverCallBack

screen = Screen()
match = screen.find(Pattern("button.png").similar(0.8))
assert isinstance(match, Match)
match.click()
screen.type("hello", 0)

options = OCR.Options().language("eng").psm(OCR.PSM.SINGLE_LINE)
text = OCR.readText("button.png", options)

# Ambiguous Java overloads can be selected explicitly.
options.psm.overload("org.sikuli.script.OCR$PSM")("SINGLE_LINE")
```

`exists()` returns `Match` or `None`, matching Java; truth checks continue to work.
Java interface callbacks accept `JavaCallback(interface_name, handler)` and
observer methods accept a Python function directly. Arrays/collections become
Python sequences; maps become dictionaries; Java iterators support iteration.

This distribution uses the matching 1.2.0b2 JVM bridge from `ajayrakde/Operix`.
The Python namespace is `pyulix`; bridge downloads are cached under `~/.pyulix/lib/`.
Java classes and upstream Maven dependency names are unchanged.

## Migration from oculix-operix

Install `pyulix` with `pip install --pre pyulix`, then change `from oculix ...`
to `from pyulix ...` (including submodules). No `oculix` compatibility
package is installed. Remove the old `oculix-operix` distribution if no longer
needed. Existing published versions are historical and do not acquire this rename.

## Status and attribution

Beta: overload ambiguity, Java `Any` types, and platform-specific desktop/OCR
behavior still require care. API coverage is not a guarantee that every argument
combination works. See the repository's `docs/` for validation and limitations.

Original work: Julien Mer and contributors. See LICENSE and NOTICE.
The separately downloaded JVM engine and native dependencies have their own licenses.
