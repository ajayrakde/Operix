"""Real Swing desktop: screen capture, OCR search, visual click and keyboard input."""
import json
import os
from pathlib import Path
import subprocess
import threading
import time
import pytest
import pyulix
from pyulix._bridge import Bridge

ROOT = Path(__file__).resolve().parents[2]
JAR = ROOT / 'jvm-bridge/target/operix-jvm-bridge-1.2.0b2.jar'
pytestmark = pytest.mark.skipif(os.environ.get('PYULIX_DESKTOP_TESTS') != '1', reason='Requires a graphical desktop')


@pytest.fixture
def desktop(monkeypatch):
    proc = subprocess.Popen(['java', '-cp', os.pathsep.join([str(JAR), str(ROOT / 'jvm-bridge/target/test-classes')]),
                             'org.operix.rpc.DesktopFixture', str(ROOT / 'test-artifacts')], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, encoding='utf-8')
    bridge = Bridge(jar_path=JAR)
    monkeypatch.setattr(pyulix, 'default_bridge', lambda: bridge)
    try:
        layout_line = proc.stdout.readline()
        if not layout_line: raise RuntimeError(proc.stderr.read())
        layout = json.loads(layout_line)
        time.sleep(0.5)  # Allow the compositor to paint the newly visible frame.
        yield bridge, proc, layout
    finally:
        (ROOT / "test-artifacts").mkdir(exist_ok=True)
        (ROOT / "test-artifacts/bridge-stderr.txt").write_text("\n".join(bridge._stderr_tail), encoding="utf-8")
        bridge.stop()
        if proc.poll() is None:
            proc.stdin.write('quit\n'); proc.stdin.flush()
            try: proc.wait(timeout=5)
            except subprocess.TimeoutExpired: proc.kill()


def region(bounds):
    return pyulix.Region(bounds['x'], bounds['y'], bounds['w'], bounds['h'])


def test_capture_find_text_click_type_and_background_observer(desktop):
    bridge, app, layout = desktop
    screen = pyulix.Screen()
    area = region(layout['region'])
    label = region(layout['label'])
    assert 'submit 12345' in label.text().casefold()
    match = label.findText('12345')
    assert isinstance(match, pyulix.Match)
    assert isinstance(match.getTarget(), pyulix.Location)
    button = region(layout['button'])
    capture = screen.capture(button)
    assert isinstance(capture, pyulix.ScreenImage)
    pixels = capture.getImage()
    assert isinstance(pixels, pyulix.BufferedImage)
    assert pixels.getWidth() > 0 and pixels.getHeight() > 0
    image_path = capture.getFile()
    found = area.find(pyulix.Pattern(image_path).similar(0.9))
    assert found.getScore() >= 0.9
    found.click()
    field = region(layout['field'])
    field.click()
    field.type('Bridge typed 123')
    field.paste(' OCR verified')
    app.stdin.write('state\n'); app.stdin.flush()
    state = json.loads(app.stdout.readline())
    assert state['clicked'] is True
    assert state['text'] == 'Bridge typed 123 OCR verified'
    event_received = threading.Event()
    events = []
    def appeared(event):
        events.append(event.getMatch())  # A nested Java call from an observer thread.
        event_received.set()
    area.onAppear(pyulix.Pattern(image_path), appeared)
    try:
        assert area.observeInBackground(5.0)
        assert event_received.wait(10), 'No background observer callback'
        assert isinstance(events[0], pyulix.Match)
        assert bridge.callback_errors == ()
    finally:
        area.stopObserver()


def test_typed_devices_gui_and_guide_on_desktop(desktop):
    bridge, app, layout = desktop
    device = pyulix.ScreenDevice.primary()
    assert isinstance(device.asRectangle(), pyulix.Rectangle)
    assert isinstance(device.getCenter(), pyulix.Point)
    robot = device.getRobot()
    assert isinstance(robot, pyulix.Robot)
    bounds = layout['label']
    rectangle = pyulix.Rectangle(bounds['x'], bounds['y'], bounds['w'], bounds['h'])
    pixels = robot.createScreenCapture(rectangle)
    assert isinstance(pixels, pyulix.BufferedImage)
    assert isinstance(robot.getPixelColor(bounds['x'], bounds['y']), pyulix.Color)
    assert '12345' in pyulix.OCR.readText(pixels)
    visual = pyulix.SxImage(pixels)
    assert isinstance(visual.getBounds(), pyulix.Rectangle)
    assert isinstance(visual.getActualSize(), pyulix.Dimension)
    overlay = pyulix.OverlayTransparentWindow(pyulix.Color.WHITE, None)
    try:
        assert isinstance(overlay.getJPanel(), pyulix.JPanel)
        assert overlay.getJPanelGraphics() is None  # Not painted yet.
        assert isinstance(overlay.getContentPane(), pyulix.Container)
    finally:
        overlay.dispose()
    # Pure resize helper covers the public SXDialog API without opening a modal.
    dialog = pyulix.SXDialog()
    try:
        assert dialog.getItem('missing') is None
        resized = dialog.adjustTo(pyulix.Rectangle(0, 0, 100, 100), pixels)
        assert isinstance(resized, pyulix.BufferedImage)
    finally:
        dialog.dispose()
