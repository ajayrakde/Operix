# oculix (Python)

Python wrapper for [OculiX](https://github.com/oculix-org/Oculix) — visual automation for the real world.

## Install

```bash
pip install oculix-operix
```

Requirements: Python 3.8+, Java 11+ on `PATH` (Eclipse Temurin or Azul Zulu).

The OculiX engine (~200 MB fat JAR) is downloaded on first use into `~/.oculix/lib/`.

## Quickstart

```python
from oculix import Screen, App, VNCScreen

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
from oculix import Screen, App

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
overload's arguments. `from oculix import Screen, OCR, Pattern` stays unchanged.
Every class is also available through `oculix.java`; nested classes keep names
such as `OCR.Options` and `OCR.PSM`.

```python
from oculix import Screen, Pattern, Match, OCR, Location, JavaCallback, ObserverCallBack

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

This distribution uses the matching 1.1.1 JVM bridge from `ajayrakde/Operix`.
Do not mix it with the older upstream bridge. It occupies the same `oculix` import
namespace as upstream, so install only one of the two distributions in a virtual
environment. See [implementation and validation](https://github.com/ajayrakde/Operix/blob/python/java-api-parity/docs/python-api-parity.md).
