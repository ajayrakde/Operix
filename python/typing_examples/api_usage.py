"""Static checks only; this module is never executed on a desktop."""
from typing import Iterable, Optional, Sequence, assert_type
from oculix import Screen, Match, Location, Pattern, OCR

screen = Screen()
assert_type(screen.findText('Submit'), Match)
assert_type(screen.findText('Submit').getTarget(), Location)
assert_type(screen.exists('button.png'), Optional[Match])
assert_type(screen.existsText('Submit'), Optional[Match])
assert_type(screen.getLastMatch(), Optional[Match])
assert_type(screen.findAll('button.png'), Iterable[Match])
assert_type(OCR.readLines('image.png'), Sequence[Match])
assert_type(Pattern('button.png').similar(0.8), Pattern)
assert_type(Location(x=3, y=4).getX(), int)

match = screen.exists('button.png')
if match is not None:
    assert_type(match.getScore(), float)

# These Java reference arguments accept null; annotations must allow it too.
OCR.readText('image.png', None)
OCR.Options().language(None)
OCR.Options().psm('SINGLE_LINE')
