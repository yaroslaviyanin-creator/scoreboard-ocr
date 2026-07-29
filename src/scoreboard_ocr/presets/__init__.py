"""Preset I/O — save/load ROI and camera configurations as JSON.

Backward-compatible format:
{
    "output_folder": "...",
    "rois": [{"name", "pos", "size", "mode", "params"}],
    "templates": {filename: base64}
}

New fields are added as optional; old presets must load without errors.
"""

import json
import base64
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

PRESET_VERSION = 2


def save_preset(
    filepath: str | Path,
    rois: list,
    output_folder: str,
    templates_dir: str | Path | None = None,
    camera_index: int | None = None,
) -> None:
    """
    Save current ROIs, output folder, and optional templates to a JSON preset.

    Args:
        filepath: Destination .json path.
        rois: List of ROIRect objects (must have name, pos, size, mode, params).
        output_folder: Current output directory for .txt files.
        templates_dir: Optional path to template images (0.png..9.png).
        camera_index: Optional camera index to restore.
    """
    filepath = Path(filepath)
    data: dict = {
        "version": PRESET_VERSION,
        "output_folder": output_folder,
        "rois": [],
        "templates": {},
    }
    if camera_index is not None:
        data["camera_index"] = camera_index

    for roi in rois:
        r = roi.rect()
        roi_data = {
            "name": roi.name,
            "pos": [roi.x(), roi.y()],
            "size": [r.width(), r.height()],
            "mode": roi.mode,
            "params": roi.params,
        }
        data["rois"].append(roi_data)

    if templates_dir:
        tpl_path = Path(templates_dir)
        if tpl_path.exists():
            for f in tpl_path.iterdir():
                if f.suffix == ".png":
                    with open(f, "rb") as img_f:
                        data["templates"][f.name] = base64.b64encode(
                            img_f.read()
                        ).decode("utf-8")

    with open(filepath, "w", encoding="utf-8") as f_out:
        json.dump(data, f_out, indent=4, ensure_ascii=False)

    logger.info("Preset saved: %s (%d ROIs)", filepath, len(data["rois"]))


def load_preset(filepath: str | Path) -> dict:
    """
    Load a preset from JSON.

    Returns a dict with:
        output_folder: str
        rois: list of dicts with name, pos, size, mode, params
        templates: dict of filename → base64 bytes
        camera_index: int or None

    Backward compatible: missing optional fields are set to defaults.
    """
    filepath = Path(filepath)
    with open(filepath, "r", encoding="utf-8") as f_in:
        data = json.load(f_in)

    result: dict = {
        "output_folder": data.get("output_folder", ""),
        "rois": data.get("rois", []),
        "templates": data.get("templates", {}),
        "camera_index": data.get("camera_index", None),
    }

    DEFAULT_PARAMS = {
        "blur": 5,
        "thresh": 130,
        "morph": 1,
        "sens": 35,
        "tilt": 0,
    }
    normalized_rois = []
    for r in result["rois"]:
        # Merge user params with defaults so missing keys don't break consumers
        user_params = r.get("params", {})
        merged_params = {**DEFAULT_PARAMS, **user_params}
        normalized_rois.append({
            "name": r.get("name", "Zone"),
            "pos": r.get("pos", [100, 100]),
            "size": r.get("size", [150, 80]),
            "mode": r.get("mode", "Standard"),
            "params": merged_params,
        })
    result["rois"] = normalized_rois

    logger.info("Preset loaded: %s (%d ROIs, %d templates, v%s)",
                filepath, len(result["rois"]), len(result["templates"]),
                data.get("version", 1))

    return result


def write_templates(templates: dict[str, str], output_dir: str | Path) -> None:
    """
    Decode and write base64-encoded template images to disk.

    Args:
        templates: Dict of filename → base64 string.
        output_dir: Directory to write template files to.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for filename, b64_data in templates.items():
        fpath = output_dir / filename
        try:
            with open(fpath, "wb") as f:
                f.write(base64.b64decode(b64_data))
            logger.debug("Template written: %s", fpath)
        except Exception as e:
            logger.warning("Failed to write template %s: %s", filename, e)

    logger.info("Wrote %d templates to %s", len(templates), output_dir)
