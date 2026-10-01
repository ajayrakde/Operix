"""Static checks only; this module is never executed on a desktop."""
from typing import Iterable, Optional, Sequence, assert_type
from oculix import Screen, Match, Location, Pattern, OCR, Image, File, URL, BufferedImage, Rectangle, Graphics2D, Visual, Point, NewAnimator, AnimationFactory, SXDialog, SXDialog_BasicItem

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
OCR.readLines('image.png', None)
OCR.Options().language(None)
OCR.Options().psm('SINGLE_LINE')

assert_type(Image.create('example.png').get(), Optional[BufferedImage])
assert_type(Image.create('example.png').file(), Optional[File])
assert_type(Image.create('example.png').getURL(), Optional[URL])
assert_type(Image.create('example.png').getLastSeen(), Optional[Rectangle])
buffer = BufferedImage(20, 20, BufferedImage.TYPE_INT_RGB)
assert_type(buffer.createGraphics(), Graphics2D)
assert_type(buffer.getWidth(), int)
assert_type(Visual().getLocation(), Point)
assert_type(AnimationFactory.createCircleAnimation(Visual(), Point(1, 2), 3.0), NewAnimator)
assert_type(SXDialog('example').getItem('missing'), Optional[SXDialog_BasicItem])
