#!/usr/bin/env python3
import argparse
import csv
import sys

from pathlib import Path
from vfj import Font


def process(font, positions):
    offsets = {}
    for glyph in font:
        for layer in glyph.layers:
            for anchor in layer.anchors:
                if not anchor.name.startswith("_"):
                    continue

                name = anchor.name[1:]

                if name not in positions:
                    continue

                x, y = positions[name]
                xoff, yoff = x - anchor.x, y - anchor.y
                anchor.x += xoff
                anchor.y += yoff

                if name not in offsets:
                    offsets[name] = (xoff, yoff)

    for glyph in font:
        for layer in glyph.layers:
            for anchor in layer.anchors:
                if anchor.name not in offsets:
                    continue

                xoff, yoff = offsets[anchor.name]
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
        positions = {row[0]: (int(row[1]), int(row[2])) for row in reader}

    process(font, positions)

    font.save(options.output)


if __name__ == "__main__":
    sys.exit(main())
