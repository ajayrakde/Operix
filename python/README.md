# oculix (Python)

Python wrapper for [OculiX](https://github.com/oculix-org/Oculix) — visual automation for the real world.

## Install

```bash
pip install oculix
```

Requirements: Python 3.8+, Java 11+ on `PATH` (Eclipse Temurin or Azul Zulu).

The OculiX engine (~160 MB fat JAR) is downloaded on first use into `~/.oculix/lib/`.

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

## Java API parity work

Known Oculix results now return their Python types: for example, `find()` and
`findText()` return `Match`, and `getTarget()` returns `Location`. Python wrappers
can be passed directly as Java method arguments. Java object identity is preserved
across returned references and chained calls.

```python
from oculix import Screen, Pattern, Match, OCR

screen = Screen()
match = screen.find(Pattern("button.png").similar(0.8))
assert isinstance(match, Match)
match.click()

options = OCR.globalOptions()
text = OCR.readText("button.png", options)
```

`exists()` now returns `Match` or `None` to match Java. Boolean checks such as
`if screen.exists("button.png"):` continue to work.

Full explicit method and overload coverage is in progress. See
[the implementation status](../docs/python-api-parity.md) for scope and remaining work.
