from __future__ import annotations

import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET


def _prop_value(prop: ET.Element) -> object:
    value = prop.get("value", "")
    prop_type = prop.get("type", "string")
    if prop_type == "int":
        return int(value or 0)
    if prop_type == "float":
        return float(value or 0)
    if prop_type == "bool":
        return value.lower() == "true"
    return value


def _parse_points(raw: str) -> list[dict[str, float]]:
    points: list[dict[str, float]] = []
    for pair in raw.split():
        x_str, y_str = pair.split(",", 1)
        points.append({"x": float(x_str), "y": float(y_str)})
    return points


def convert_tmx_to_json(source: Path, target: Path) -> None:
    root = ET.parse(source).getroot()
    output: dict[str, object] = {
        "type": "map",
        "version": root.get("version"),
        "tiledversion": root.get("tiledversion"),
        "orientation": root.get("orientation"),
        "renderorder": root.get("renderorder"),
        "width": int(root.get("width", "0")),
        "height": int(root.get("height", "0")),
        "tilewidth": int(root.get("tilewidth", "0")),
        "tileheight": int(root.get("tileheight", "0")),
        "infinite": False,
        "layers": [],
    }
    layers: list[dict[str, object]] = []
    for group in root.findall("objectgroup"):
        layer: dict[str, object] = {
            "id": int(group.get("id", "0")),
            "name": group.get("name", ""),
            "type": "objectgroup",
            "visible": True,
            "opacity": 1,
            "objects": [],
        }
        objects: list[dict[str, object]] = []
        for obj in group.findall("object"):
            item: dict[str, object] = {
                "id": int(obj.get("id", "0")),
                "name": obj.get("name", ""),
                "type": obj.get("type", ""),
                "x": float(obj.get("x", "0")),
                "y": float(obj.get("y", "0")),
                "width": float(obj.get("width", "0")),
                "height": float(obj.get("height", "0")),
                "rotation": 0,
                "visible": True,
            }
            props_el = obj.find("properties")
            if props_el is not None:
                item["properties"] = [
                    {
                        "name": prop.get("name", ""),
                        "type": prop.get("type", "string"),
                        "value": _prop_value(prop),
                    }
                    for prop in props_el.findall("property")
                ]
            polyline = obj.find("polyline")
            if polyline is not None:
                item["polyline"] = _parse_points(polyline.get("points", ""))
            objects.append(item)
        layer["objects"] = objects
        layers.append(layer)
    output["layers"] = layers
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: export_tiled_level.py SOURCE.tmx TARGET.json", file=sys.stderr)
        return 2
    convert_tmx_to_json(Path(sys.argv[1]), Path(sys.argv[2]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
