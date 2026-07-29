"""Tests for preset save/load (preset_io.py)."""

import json
import tempfile
import os
import pytest
from scoreboard_ocr.presets import save_preset, load_preset, write_templates


class FakeROI:
    """Minimal ROI-like object for testing preset I/O."""

    def __init__(self, x, y, w, h, name="TestZone", mode="Standard", params=None):
        self._x = x
        self._y = y
        self._w = w
        self._h = h
        self.name = name
        self.mode = mode
        self.params = params or {
            "blur": 5, "thresh": 130, "morph": 1, "sens": 35, "tilt": 0,
        }

    def x(self):
        return self._x

    def y(self):
        return self._y

    def rect(self):
        class R:
            def width(self):
                return self.w
            def height(self):
                return self.h
        r = R()
        r.w = self._w
        r.h = self._h
        return r


class TestPresetRoundTrip:
    """Save and load a preset — round-trip test."""

    def test_round_trip_no_templates(self):
        """Save with ROIs, load back, verify data matches."""
        rois = [
            FakeROI(100, 200, 150, 80, name="Score", mode="Standard"),
            FakeROI(300, 200, 120, 60, name="Time", mode="Time", params={
                "blur": 7, "thresh": 140, "morph": 2, "sens": 40, "tilt": 0,
            }),
            FakeROI(500, 100, 200, 40, name="TeamName", mode="Name"),
        ]

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            preset_path = f.name

        try:
            save_preset(preset_path, rois, "/tmp/vmix_output")

            data = load_preset(preset_path)

            assert data["output_folder"] == "/tmp/vmix_output"
            assert len(data["rois"]) == 3
            assert data["rois"][0]["name"] == "Score"
            assert data["rois"][1]["name"] == "Time"
            assert data["rois"][1]["params"]["thresh"] == 140
            assert data["rois"][2]["name"] == "TeamName"
            assert data["rois"][2]["mode"] == "Name"
        finally:
            os.unlink(preset_path)

    def test_load_old_format_missing_fields(self):
        """Loading a minimal old-format preset (no version, no optional fields) should work."""
        old_data = {
            "output_folder": "/tmp/old",
            "rois": [
                {
                    "name": "OldZone",
                    "pos": [10, 20],
                    "size": [100, 50],
                    "mode": "Standard",
                    "params": {"blur": 3},
                }
            ],
            "templates": {},
        }
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump(old_data, f)
            preset_path = f.name

        try:
            data = load_preset(preset_path)
            assert data["output_folder"] == "/tmp/old"
            assert len(data["rois"]) == 1
            assert data["rois"][0]["name"] == "OldZone"
            # Missing params keys should have defaults
            roi = data["rois"][0]
            assert roi["params"]["blur"] == 3  # provided
            assert roi["params"]["thresh"] == 130  # default
            assert roi["params"]["morph"] == 1  # default
        finally:
            os.unlink(preset_path)

    def test_load_old_format_no_params(self):
        """Loading a preset without params at all should not crash."""
        old_data = {
            "output_folder": "",
            "rois": [
                {
                    "name": "Bare",
                    "pos": [5, 5],
                    "size": [80, 30],
                }
            ],
        }
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump(old_data, f)
            preset_path = f.name

        try:
            data = load_preset(preset_path)
            assert data["rois"][0]["mode"] == "Standard"  # default mode
        finally:
            os.unlink(preset_path)


class TestWriteTemplates:
    """Template writing tests."""

    def test_write_templates_to_dir(self):
        """Base64 templates should be decoded and written to disk."""
        import base64
        # A minimal 1x1 white PNG in base64
        minimal_png_b64 = (
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADU"
            "lEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
        )
        templates = {"0.png": minimal_png_b64}

        with tempfile.TemporaryDirectory() as tmpdir:
            write_templates(templates, tmpdir)
            result = os.path.join(tmpdir, "0.png")
            assert os.path.exists(result)
            with open(result, "rb") as f:
                data = f.read()
            assert len(data) > 0
            assert base64.b64encode(data).decode() == minimal_png_b64
