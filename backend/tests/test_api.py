"""Unit and API verification tests for Mustakshef-AI FastAPI backend."""

import base64
import io
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

os.environ["AUTO_DOWNLOAD_MODEL"] = "0"

import main  # noqa: E402


def _make_png_bytes(width: int = 120, height: int = 80, color=(20, 140, 90)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color).save(buf, format="PNG")
    return buf.getvalue()


class _ScalarTensor:
    def __init__(self, value: float):
        self._value = value

    def item(self) -> float:
        return self._value


class _FakeArray:
    def __init__(self, values):
        self._values = [_ScalarTensor(v) for v in values]

    def __getitem__(self, idx: int) -> _ScalarTensor:
        return self._values[idx]

    def argmax(self) -> _ScalarTensor:
        max_idx = max(range(len(self._values)), key=lambda i: self._values[i].item())
        return _ScalarTensor(max_idx)


class _FakeBoxes:
    def __init__(self, confs, cls_ids):
        self.conf = _FakeArray(confs)
        self.cls = _FakeArray(cls_ids)

    def __len__(self) -> int:
        return len(self.cls._values)


class _FakeResult:
    def __init__(self, image: Image.Image, boxes: _FakeBoxes, names: dict):
        self._image = image
        self.boxes = boxes
        self.names = names

    def plot(self, masks: bool = True, boxes: bool = True, labels: bool = False):
        return np.array(self._image)


class _FakeYOLO:
    def __init__(self, class_name: str = "Apple", confidence: float = 0.91, empty: bool = False):
        self.names = {idx: name for idx, name in enumerate(main.CLASS_NAMES_AR.keys())}
        self._empty = empty
        self._confidence = confidence
        self._cls_id = next((k for k, v in self.names.items() if v == class_name), 1)

    def __call__(self, image: Image.Image, conf: float = 0.25, task: str = "segment"):
        if self._empty:
            return [_FakeResult(image, _FakeBoxes([], []), self.names)]
        return [_FakeResult(image, _FakeBoxes([self._confidence], [self._cls_id]), self.names)]


@pytest.fixture(autouse=True)
def _reset_runtime(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "yolo_model", None)
    monkeypatch.setattr(main, "MODEL_PATH", str(tmp_path / "missing_weights.pt"))
    monkeypatch.setenv("AUTO_DOWNLOAD_MODEL", "0")


def test_spell_word_and_phonics_helpers():
    assert main.spell_word("تُفَّاحَة") == ["ت", "ف", "ا", "ح", "ة"]
    assert main.spell_word("مَ وْ ز") == ["م", "و", "ز"]
    assert main.spoken_form("ة") == "تاء مربوطة"
    assert main.spoken_form("تفاحة") == "تفاحة"
    assert isinstance(main.render_arabic_text("تفاحة"), str)


def test_center_square_crop_preserves_square_geometry():
    rect = Image.new("RGB", (200, 100), (0, 0, 0))
    cropped = main.center_square_crop(rect, guide_ratio=0.8)
    assert cropped.size == (80, 80)

    tiny = Image.new("RGB", (1, 1), (0, 0, 0))
    assert main.center_square_crop(tiny).size == (1, 1)


def test_root_health_and_labels_reflect_loaded_model(monkeypatch):
    with TestClient(main.app) as client:
        r_root = client.get("/")
        assert r_root.status_code == 200
        assert r_root.json()["classes_count"] == 82

        r_degraded = client.get("/health")
        assert r_degraded.status_code == 200
        assert r_degraded.json() == {"status": "degraded", "yolo_ready": False, "classes": 0}

        monkeypatch.setattr(main, "yolo_model", _FakeYOLO())
        r_healthy = client.get("/health")
        assert r_healthy.status_code == 200
        assert r_healthy.json() == {"status": "healthy", "yolo_ready": True, "classes": 82}

        r_labels = client.get("/labels")
        assert r_labels.status_code == 200
        classes = r_labels.json()["classes"]
        assert len(classes) == 82
        assert any(c["label_en"] == "Apple" and c["label_ar"] == "تفاحة" for c in classes)


def test_segment_valid_detection_with_concurrent_phonics(monkeypatch):
    monkeypatch.setattr(main, "yolo_model", _FakeYOLO(class_name="Apple", confidence=0.92))

    async def fake_tts(text: str, voice: str = main.DEFAULT_VOICE):
        return f"audio:{voice}:{text}".encode("utf-8")

    monkeypatch.setattr(main, "generate_speech_bytes", fake_tts)

    with TestClient(main.app) as client:
        resp = client.post(
            "/segment?voice=ar-SA-HamedNeural",
            files={"file": ("apple.png", _make_png_bytes(), "image/png")},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["detected"] is True
    assert body["label_en"] == "Apple"
    assert body["label_ar"] == "تفاحة"
    assert pytest.approx(body["confidence"], rel=1e-4) == 0.92
    assert body["inference_ms"] >= 0
    assert body["spelling"] == ["ت", "ف", "ا", "ح", "ة"]
    assert [item["name"] for item in body["spelling_details"]] == [
        "تاء",
        "فاء",
        "ألف",
        "حاء",
        "تاء مربوطة",
    ]
    assert body["annotated_image"].startswith("data:image/jpeg;base64,")
    decoded_img = Image.open(io.BytesIO(base64.b64decode(body["annotated_image"].split(",", 1)[1])))
    assert decoded_img.format == "JPEG"
    assert body["audio_word"].startswith("data:audio/mp3;base64,")
    assert all(item["audio"].startswith("data:audio/mp3;base64,") for item in body["spelling_details"])


def test_segment_no_detection_returns_honest_empty_state(monkeypatch):
    monkeypatch.setattr(main, "yolo_model", _FakeYOLO(empty=True))

    with TestClient(main.app) as client:
        resp = client.post(
            "/api/segment",
            files={"file": ("blank.png", _make_png_bytes(), "image/png")},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["detected"] is False
    assert body["label_en"] == "Unrecognized"
    assert body["confidence"] == 0.0
    assert body["spelling"] == []
    assert body["spelling_details"] == []
    assert body["audio_word"] is None
    assert body["annotated_image"].startswith("data:image/jpeg;base64,")


def test_segment_rejects_missing_model_and_invalid_inputs(monkeypatch):
    with TestClient(main.app) as client:
        # Model unloaded -> 503
        r_503 = client.post("/segment", files={"file": ("a.png", _make_png_bytes(), "image/png")})
        assert r_503.status_code == 503

        monkeypatch.setattr(main, "yolo_model", _FakeYOLO())

        # Empty upload -> 400
        r_empty = client.post("/segment", files={"file": ("empty.png", b"", "image/png")})
        assert r_empty.status_code == 400

        # Non-image upload -> 400
        r_bad = client.post("/segment", files={"file": ("bad.txt", b"not-an-image", "text/plain")})
        assert r_bad.status_code == 400

        # Oversized upload -> 413
        monkeypatch.setattr(main, "MAX_IMAGE_BYTES", 32)
        r_big = client.post("/segment", files={"file": ("big.png", _make_png_bytes(), "image/png")})
        assert r_big.status_code == 413


def test_tts_endpoint_validation_and_response(monkeypatch):
    async def fake_tts(text: str, voice: str = main.DEFAULT_VOICE):
        if text == "fail":
            return None
        return b"ID3-MOCK-MP3"

    monkeypatch.setattr(main, "generate_speech_bytes", fake_tts)

    with TestClient(main.app) as client:
        r_ok = client.get("/api/tts", params={"text": "موز", "voice": main.MALE_VOICE})
        assert r_ok.status_code == 200
        assert r_ok.headers["content-type"].startswith("audio/mp3")
        assert r_ok.content == b"ID3-MOCK-MP3"

        r_bad_voice = client.get("/api/tts", params={"text": "موز", "voice": "invalid-voice"})
        assert r_bad_voice.status_code == 400

        r_fail = client.get("/api/tts", params={"text": "fail"})
        assert r_fail.status_code == 500
