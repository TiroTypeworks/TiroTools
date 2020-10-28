#!/usr/bin/env python3
import argparse
import csv
import sys

from pathlib import Path
from vfj import Font


def process(font, positions):
    offsets = {}
    for name in positions:
        gname, x, y = positions[name]
        glyph = font[gname]
        for layer in glyph.layers:
            if layer.name not in offsets:
                offsets[layer.name] = {}
            for anchor in layer.anchors:
                if anchor.name == name:
                    xoff, yoff = x - anchor.x, y - anchor.y
                    offsets[layer.name][name[1:]] = (xoff, yoff)

    for glyph in font:
        for layer in glyph.layers:
            for anchor in layer.anchors:
                name = anchor.name
                if name.startswith("_"):
                    name = name[1:]

                if name not in offsets[layer.name]:
                    continue

                xoff, yoff = offsets[layer.name][name]
                anchor.x += xoff
                anchor.y += yoff


def main(args=None):
    parser = argparse.ArgumentParser(
        description="Move anchor to new positions in FontLab VFJ files."
    )
    parser.add_argument("input", type=Path, help="input VFJ file")
    parser.add_argument("output", type=Path, help="output VFJ file")
    parser.add_argument(
        "-p",
        "--positions",
        type=Path,
        required=True,
        help="CSV file with new anchor positions",
    )

    options = parser.parse_args(args)

    font = Font(options.input)
    with open(options.positions) as f:
        reader = csv.reader(f)
        positions = {row[0]: (row[1], int(row[2]), int(row[3])) for row in reader}

    process(font, positions)

    font.save(options.output)


if __name__ == "__main__":
    sys.exit(main())
