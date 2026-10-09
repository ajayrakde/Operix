"""Transport-level tests that do not require a desktop or a bridge JAR."""

import gc
import json
import sys
from pathlib import Path

import pytest

import pyulix
from pyulix._bridge import Bridge, RemoteObject, _decode, _encode


class RecordingBridge(Bridge):
    def __init__(self):
        super().__init__(jar_path=Path('/unused.jar'), java_bin=sys.executable)
        self.requests = []
        self.released = []
        self.result = None

    def _request(self, payload):
        if 'resolve' in payload:
            # This transport fake does not implement Java's type graph. Real JVM
            # tests cover resolution; choose the string candidate used here.
            return next((i for i, candidate in enumerate(payload['candidates'])
                        if candidate['parameter_types'] == ['java.lang.String']), 0)
        # Exercise actual JSON encoding, not merely the in-memory request shape.
        self.requests.append(json.loads(json.dumps(payload)))
        return self.result

    def release(self, ref):
        self.released.append(ref)


@pytest.fixture
def bridge(monkeypatch):
    value = RecordingBridge()
    monkeypatch.setattr(pyulix, 'default_bridge', lambda: value)
    return value


def ref(java_class, handle='o1'):
    return {'__ref': handle, '__class': java_class}


@pytest.mark.parametrize('wrapper', [
    pyulix.Region, pyulix.Screen, pyulix.Match, pyulix.Pattern,
    pyulix.Location, pyulix.Image, pyulix.ScreenImage, pyulix.App,
    pyulix.VNCScreen, pyulix.ADBScreen, pyulix.SSHTunnel,
    pyulix.PaddleOCREngine, pyulix.PaddleOCRClient,
    pyulix.TesseractEngine, pyulix.OCR.Options,
])
def test_known_runtime_class_returns_typed_wrapper(bridge, wrapper):
    value = _decode(bridge, ref(wrapper.JAVA_CLASS))
    assert isinstance(value, wrapper)
    assert _decode(bridge, ref(wrapper.JAVA_CLASS)) is value
    assert _encode(value, bridge) == {'__ref': 'o1'}


def test_external_class_gets_named_typed_proxy(bridge):
    value = _decode(bridge, ref('java.lang.StringBuilder'))
    assert isinstance(value, pyulix.JavaObject)
    assert value.JAVA_CLASS == "java.lang.StringBuilder"
    bridge.result = 3
    assert value.length() == 3


def test_constructor_interns_public_instance_and_keeps_reference_alive(bridge):
    bridge.result = ref(pyulix.Pattern.JAVA_CLASS)
    pattern = pyulix.Pattern('button.png')
    gc.collect()
    assert _decode(bridge, bridge.result) is pattern
    assert bridge.released == []
    assert pattern.similar(0.8) is pattern
    del pattern
    gc.collect()
    assert bridge.released == ['o1']


def test_find_returns_match_and_accepts_pattern_argument(bridge):
    screen = _decode(bridge, ref(pyulix.Screen.JAVA_CLASS, 'screen'))
    pattern = _decode(bridge, ref(pyulix.Pattern.JAVA_CLASS, 'pattern'))
    bridge.result = ref(pyulix.Match.JAVA_CLASS, 'match')
    match = screen.find(pattern)
    assert isinstance(match, pyulix.Match)
    assert isinstance(match, pyulix.Region)
    assert bridge.requests[-1]['args'] == [{'__ref': 'pattern'}]
    bridge.result = 0.97
    assert match.getScore() == 0.97


def test_same_ref_chain_preserves_typed_identity(bridge):
    region = _decode(bridge, ref(pyulix.Region.JAVA_CLASS))
    bridge.result = ref(pyulix.Region.JAVA_CLASS)
    assert region.setX(42) is region


def test_static_factory_does_not_double_wrap(bridge):
    bridge.result = ref(pyulix.App.JAVA_CLASS)
    app = pyulix.App.open('notepad')
    assert isinstance(app._remote, RemoteObject)
    assert pyulix.App._wrap(app) is app
    assert _decode(bridge, bridge.result) is app
    assert _encode(app, bridge) == {'__ref': 'o1'}


def test_exists_preserves_java_match_or_null_result(bridge):
    screen = _decode(bridge, ref(pyulix.Screen.JAVA_CLASS, 'screen'))
    bridge.result = ref(pyulix.Match.JAVA_CLASS)
    assert isinstance(screen.exists('button.png'), pyulix.Match)
    bridge.result = None
    assert screen.exists('missing.png') is None


def test_ocr_options_roundtrip(bridge):
    bridge.result = ref(pyulix.OCR.Options.JAVA_CLASS)
    options = pyulix.OCR.globalOptions()
    assert isinstance(options, pyulix.OCR.Options)
    bridge.result = 'Submit'
    assert pyulix.OCR.readText('button.png', options) == 'Submit'
    assert bridge.requests[-1]['args'] == ['button.png', {'__ref': 'o1'}]


def test_codec_handles_nested_wrappers_and_results(bridge):
    region = _decode(bridge, ref(pyulix.Region.JAVA_CLASS))
    assert _encode({'items': [region, (region,)]}, bridge) == {
        'items': [{'__ref': 'o1'}, [{'__ref': 'o1'}]],
    }
    result = _decode(bridge, {'items': [ref(pyulix.Region.JAVA_CLASS)]})
    assert result['items'][0] is region


def test_cross_bridge_arguments_are_rejected_before_request(bridge):
    other = RecordingBridge()
    pattern = _decode(other, ref(pyulix.Pattern.JAVA_CLASS))
    with pytest.raises(ValueError, match='different JVM bridge'):
        bridge.call('screen', 'find', [pattern])
    assert bridge.requests == []


def test_raw_ref_dictionary_is_map_data_and_cannot_forge_reference(bridge):
    assert _encode({'__ref': 'another-jvm-object'}, bridge) == {
        '__map': [['__ref', 'another-jvm-object']],
    }


def test_live_typed_alias_is_not_released_when_other_alias_is_deleted(bridge):
    value = _decode(bridge, ref(pyulix.Match.JAVA_CLASS))
    alias = _decode(bridge, ref(pyulix.Match.JAVA_CLASS))
    del value
    gc.collect()
    assert bridge.released == []
    del alias
    gc.collect()
    assert bridge.released == ['o1']


def test_typed_result_keeps_unwrapped_methods_directly_callable(bridge):
    image = _decode(bridge, ref(pyulix.Image.JAVA_CLASS))
    bridge.result = 240
    assert image.getW() == 240
    assert bridge.requests[-1]['method'] == 'getW'
    with pytest.raises(AttributeError):
        getattr(image, '__getstate_missing__')


def test_find_text_returns_typed_match(bridge):
    screen = _decode(bridge, ref(pyulix.Screen.JAVA_CLASS, 'screen'))
    bridge.result = ref(pyulix.Match.JAVA_CLASS, 'match')
    match = screen.findText('Submit')
    assert isinstance(match, pyulix.Match)
    assert bridge.requests[-1]['args'] == ['Submit']


def test_ocr_read_text_selects_omitted_or_explicit_options(bridge):
    bridge.result = 'text'
    assert pyulix.OCR.readText('image.png') == 'text'
    assert bridge.requests[-1]['args'] == ['image.png']
    with pytest.raises(TypeError, match='options.*must not be None'):
        pyulix.OCR.readText('image.png', None)
    assert pyulix.OCR.readLines('image.png', None) == 'text'
    assert bridge.requests[-1]['args'] == ['image.png', None]
