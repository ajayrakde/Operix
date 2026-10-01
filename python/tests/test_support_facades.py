"""Real JVM round trips for dependency facades and opaque Java return types."""
from pathlib import Path
import pytest
import oculix
from oculix._bridge import Bridge

JAR = Path(__file__).resolve().parents[2] / 'jvm-bridge/target/operix-jvm-bridge-1.2.0b1.jar'
pytestmark = pytest.mark.skipif(not JAR.exists(), reason='Build the beta bridge JAR')


@pytest.fixture
def bridge(monkeypatch):
    b = Bridge(jar_path=JAR)
    monkeypatch.setattr(oculix, 'default_bridge', lambda: b)
    try:
        yield b
    finally:
        b.stop()


def test_geometry_fields_and_returned_image_round_trip(bridge):
    image = oculix.BufferedImage(32, 24, oculix.BufferedImage.TYPE_INT_RGB)
    assert isinstance(image, oculix.JavaImage)
    assert image.getWidth() == 32
    assert image.getHeight() == 24
    rect = oculix.Rectangle(2, 3, 10, 8)
    assert rect.x == 2 and rect.height == 8
    rect.x = 4
    assert rect.getX() == 4.0
    cropped = oculix.Image.createSubimage(image, rect)
    assert isinstance(cropped, oculix.BufferedImage)
    assert cropped.getWidth() == 10
    assert cropped.getHeight() == 8
    pattern = oculix.Pattern(cropped)
    assert isinstance(pattern.getBImage(), oculix.BufferedImage)
    assert pattern.getBImage()._ref == cropped._ref


def test_runtime_graphics_subclass_retains_public_facade(bridge):
    image = oculix.BufferedImage(20, 20, oculix.BufferedImage.TYPE_INT_RGB)
    graphics = image.createGraphics()
    assert isinstance(graphics, oculix.Graphics2D)
    assert graphics._remote._class != 'java.awt.Graphics2D'
    try:
        graphics.setColor(oculix.Color.RED)
        graphics.fillRect(0, 0, 20, 20)
    finally:
        graphics.dispose()
    assert image.getRGB(2, 3) == oculix.Color.RED.getRGB()


def test_file_url_reader_and_nullable_image_metadata(bridge, tmp_path):
    text = tmp_path / 'support.txt'
    text.write_text('typed reader\n', encoding='utf-8')
    file = oculix.Commons.asFile(str(text))
    assert isinstance(file, oculix.File)
    assert file.exists()
    url = oculix.Commons.makeURL(file)
    assert isinstance(url, oculix.URL)
    assert url.getProtocol() == 'file'
    assert oculix.Commons.urlToFile(url).getAbsolutePath() == file.getAbsolutePath()
    reader = oculix.ImagePath.open(str(text))
    assert isinstance(reader, oculix.BufferedReader)
    try:
        assert reader.readLine() == 'typed reader'
        assert reader.readLine() is None
    finally:
        reader.close()
    image = oculix.Image.create.overload('java.lang.String')(None)
    assert image.getURL() is None
    assert image.file() is None
    assert image.getLastSeen() is None
    assert image.get() is None


def test_mat_conversion_and_release(bridge):
    image = oculix.BufferedImage(20, 15, oculix.BufferedImage.TYPE_INT_RGB)
    matrix = oculix.Commons.makeMat(image)
    assert isinstance(matrix, oculix.Mat)
    try:
        assert matrix.rows() == 15 and matrix.cols() == 20
        restored = oculix.Commons.getBufferedImage(matrix)
        assert isinstance(restored, oculix.BufferedImage)
        assert restored.getWidth() == 20
    finally:
        matrix.release()


def test_inherited_geometry_and_opaque_animation_handle(bridge):
    visual = oculix.Visual()
    assert isinstance(visual.getBounds(), oculix.Rectangle)
    assert isinstance(visual.getLocation(), oculix.Point)
    animation = oculix.AnimationFactory.createCircleAnimation(visual, oculix.Point(10, 10), 10.0)
    assert isinstance(animation, oculix.NewAnimator)
    with pytest.raises(AttributeError, match='opaque Java handle'):
        animation.setLooping(True)
    visual.addAnimation(animation)


def test_reviewed_null_guards_preserve_supported_nulls(bridge):
    with pytest.raises(TypeError, match='options.*must not be None'):
        oculix.OCR.readText('unused.png', None)
    with pytest.raises(TypeError, match='psm.*must not be None'):
        oculix.OCR.Options().psm(None)
    with pytest.raises(TypeError, match='loc.*must not be None'):
        oculix.Pattern().targetOffset(None)
    with pytest.raises(TypeError, match='must not be None'):
        oculix.Image.create.overload('java.io.File')(None)
    assert not oculix.Pattern.overload('java.lang.String')(None).isValid()


def test_ocr_reads_typed_buffered_image(bridge):
    fixture = Path(__file__).parent / 'fixtures/ocr-submit.png'
    image = oculix.Image.create(str(fixture)).get()
    assert isinstance(image, oculix.BufferedImage)
    assert '12345' in oculix.OCR.readText(image)
    assert oculix.OCR.readLines(image, None)
