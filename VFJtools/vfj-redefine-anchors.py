#!/usr/bin/env python3
import argparse
import csv
import re
import sys
import logging
from collections import defaultdict

from pathlib import Path
from vfj import Font

logging.basicConfig(format="%(levelname)s: %(message)s")
log = logging.getLogger()


def debom(string):
    """Strip BOM from strings."""
    return string.encode("utf-8").decode("utf-8-sig")


def process(font, positions):
    offsets = defaultdict(dict)
    for (lname, name), (gname, x, y) in positions.items():
        glyph = font[gname]
        if glyph is None:
            log.warning(f"Glyph '{gname}' is missing from font")
            continue

        for layer in glyph.layers:
            if lname is not None and layer.name != lname:
                continue

            basename = name
            if name.startswith("_"):
                basename = name[1:]

            if basename in offsets[layer.name]:
                log.error(f"Anchor '{basename}' already processed")
                return False

            for anchor in layer.anchors:
                if anchor.name == name:
                    xoff, yoff = x - anchor.x, y - anchor.y
                    offsets[layer.name][basename] = (xoff, yoff)

            if basename not in offsets[layer.name]:
                log.warning(f"Glyph '{gname}' does not have anchor named '{name}'")

    for glyph in font:
        for layer in glyph.layers:
            for anchor in layer.anchors:
                name = anchor.name
                if name.startswith("_"):
                    name = name[1:]
                elif "_" in name:
                    name, _ = name.split("_", 2)

                if name not in offsets[layer.name]:
                    continue

                xoff, yoff = offsets[layer.name][name]
                anchor.x += xoff
                anchor.y += yoff

    return True


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

    layers = {l.name for g in font for l in g.layers}

    positions = {}
    layer_re = re.compile(r"^\s*#\s*layer:\s*(.+?)\s*$")
    layer = None
    with open(options.positions) as f:
        reader = csv.reader(f)
        for row in reader:
            row = [debom(c) for c in row]

            if m := layer_re.match(row[0]):
                layer = m.group(1)
                if layer not in layers:
                    log.warning(
                        f"Layer '{layer}' does not exist in font, "
                        "all anchor redefinitions for this layer will be ignored."
                    )
                continue

            if len(row) != 4:
                log.error("Invalid CSV data, there must exactly 4 columns.")
                return 1

            if (layer, row[0]) in positions:
                log.warning(
                    f"Anchor '{row[0]}' is already set for another glyph, ignoring."
                )
                continue

            row = [debom(c) for c in row]
            positions[(layer, row[0])] = (row[1], int(row[2]), int(row[3]))

    if not process(font, positions):
        return 2

    font.save(options.output)


if __name__ == "__main__":
    sys.exit(main())
