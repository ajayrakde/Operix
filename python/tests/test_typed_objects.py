"""Transport-level tests that do not require a desktop or a bridge JAR."""

import gc
import json
import sys
from pathlib import Path

import pytest

import oculix
from oculix._bridge import Bridge, RemoteObject, _decode, _encode


class RecordingBridge(Bridge):
    def __init__(self):
        super().__init__(jar_path=Path('/unused.jar'), java_bin=sys.executable)
        self.requests = []
        self.released = []
        self.result = None

    def _request(self, payload):
        # Exercise actual JSON encoding, not merely the in-memory request shape.
        self.requests.append(json.loads(json.dumps(payload)))
        return self.result

    def release(self, ref):
        self.released.append(ref)


@pytest.fixture
def bridge(monkeypatch):
    value = RecordingBridge()
    monkeypatch.setattr(oculix, 'default_bridge', lambda: value)
    return value


def ref(java_class, handle='o1'):
    return {'__ref': handle, '__class': java_class}


@pytest.mark.parametrize('wrapper', [
    oculix.Region, oculix.Screen, oculix.Match, oculix.Pattern,
    oculix.Location, oculix.Image, oculix.ScreenImage, oculix.App,
    oculix.VNCScreen, oculix.ADBScreen, oculix.SSHTunnel,
    oculix.PaddleOCREngine, oculix.PaddleOCRClient,
    oculix.TesseractEngine, oculix.OCR.Options,
])
def test_known_runtime_class_returns_typed_wrapper(bridge, wrapper):
    value = _decode(bridge, ref(wrapper.JAVA_CLASS))
    assert isinstance(value, wrapper)
    assert _decode(bridge, ref(wrapper.JAVA_CLASS)) is value
    assert _encode(value, bridge) == {'__ref': 'o1'}


def test_external_class_gets_named_typed_proxy(bridge):
    value = _decode(bridge, ref('java.lang.StringBuilder'))
    assert isinstance(value, oculix.JavaObject)
    assert value.JAVA_CLASS == "java.lang.StringBuilder"
    bridge.result = 3
    assert value.length() == 3


def test_constructor_interns_public_instance_and_keeps_reference_alive(bridge):
    bridge.result = ref(oculix.Pattern.JAVA_CLASS)
    pattern = oculix.Pattern('button.png')
    gc.collect()
    assert _decode(bridge, bridge.result) is pattern
    assert bridge.released == []
    assert pattern.similar(0.8) is pattern
    del pattern
    gc.collect()
    assert bridge.released == ['o1']


def test_find_returns_match_and_accepts_pattern_argument(bridge):
    screen = _decode(bridge, ref(oculix.Screen.JAVA_CLASS, 'screen'))
    pattern = _decode(bridge, ref(oculix.Pattern.JAVA_CLASS, 'pattern'))
    bridge.result = ref(oculix.Match.JAVA_CLASS, 'match')
    match = screen.find(pattern)
    assert isinstance(match, oculix.Match)
    assert isinstance(match, oculix.Region)
    assert bridge.requests[-1]['args'] == [{'__ref': 'pattern'}]
    bridge.result = 0.97
    assert match.getScore() == 0.97


def test_same_ref_chain_preserves_typed_identity(bridge):
    region = _decode(bridge, ref(oculix.Region.JAVA_CLASS))
    bridge.result = ref(oculix.Region.JAVA_CLASS)
    assert region.setX(42) is region


def test_static_factory_does_not_double_wrap(bridge):
    bridge.result = ref(oculix.App.JAVA_CLASS)
    app = oculix.App.open('notepad')
    assert isinstance(app._remote, RemoteObject)
    assert oculix.App._wrap(app) is app
    assert _decode(bridge, bridge.result) is app
    assert _encode(app, bridge) == {'__ref': 'o1'}


def test_exists_preserves_java_match_or_null_result(bridge):
    screen = _decode(bridge, ref(oculix.Screen.JAVA_CLASS, 'screen'))
    bridge.result = ref(oculix.Match.JAVA_CLASS)
    assert isinstance(screen.exists('button.png'), oculix.Match)
    bridge.result = None
    assert screen.exists('missing.png') is None


def test_ocr_options_roundtrip(bridge):
    bridge.result = ref(oculix.OCR.Options.JAVA_CLASS)
    options = oculix.OCR.globalOptions()
    assert isinstance(options, oculix.OCR.Options)
    bridge.result = 'Submit'
    assert oculix.OCR.readText('button.png', options) == 'Submit'
    assert bridge.requests[-1]['args'] == ['button.png', {'__ref': 'o1'}]


def test_codec_handles_nested_wrappers_and_results(bridge):
    region = _decode(bridge, ref(oculix.Region.JAVA_CLASS))
    assert _encode({'items': [region, (region,)]}, bridge) == {
        'items': [{'__ref': 'o1'}, [{'__ref': 'o1'}]],
    }
    result = _decode(bridge, {'items': [ref(oculix.Region.JAVA_CLASS)]})
    assert result['items'][0] is region


def test_cross_bridge_arguments_are_rejected_before_request(bridge):
    other = RecordingBridge()
    pattern = _decode(other, ref(oculix.Pattern.JAVA_CLASS))
    with pytest.raises(ValueError, match='different JVM bridge'):
        bridge.call('screen', 'find', [pattern])
    assert bridge.requests == []


def test_raw_ref_dictionaries_cannot_bypass_bridge_ownership(bridge):
    with pytest.raises(ValueError, match='raw __ref'):
        bridge.call('screen', 'find', [{'__ref': 'another-jvm-object'}])
    assert bridge.requests == []


def test_live_typed_alias_is_not_released_when_other_alias_is_deleted(bridge):
    value = _decode(bridge, ref(oculix.Match.JAVA_CLASS))
    alias = _decode(bridge, ref(oculix.Match.JAVA_CLASS))
    del value
    gc.collect()
    assert bridge.released == []
    del alias
    gc.collect()
    assert bridge.released == ['o1']


def test_typed_result_keeps_unwrapped_methods_directly_callable(bridge):
    image = _decode(bridge, ref(oculix.Image.JAVA_CLASS))
    bridge.result = 240
    assert image.getW() == 240
    assert bridge.requests[-1]['method'] == 'getW'
    with pytest.raises(AttributeError):
        getattr(image, '__getstate_missing__')


def test_find_text_returns_typed_match(bridge):
    screen = _decode(bridge, ref(oculix.Screen.JAVA_CLASS, 'screen'))
    bridge.result = ref(oculix.Match.JAVA_CLASS, 'match')
    match = screen.findText('Submit')
    assert isinstance(match, oculix.Match)
    assert bridge.requests[-1]['args'] == ['Submit']


def test_ocr_read_text_selects_omitted_or_explicit_options(bridge):
    bridge.result = 'text'
    assert oculix.OCR.readText('image.png') == 'text'
    assert bridge.requests[-1]['args'] == ['image.png']
    assert oculix.OCR.readText('image.png', None) == 'text'
    assert bridge.requests[-1]['args'] == ['image.png', None]
