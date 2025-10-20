#!/usr/bin/env python3
import argparse
import logging
import math
import sys
from pathlib import Path

from fontTools.misc.fixedTools import otRound
from fontTools.misc.transform import Identity
from vfj import Font

log = logging.getLogger()


def process(font, transform):
    for glyph in font:
        for layer in glyph.layers:
            for anchor in layer.anchors:
                x, y = transform.transformPoint((anchor.x, anchor.y))
                anchor.x = otRound(x)
                anchor.y = otRound(y)


def main(args=None):
    parser = argparse.ArgumentParser(
        description="Transform X anchor positions in VFJ files."
    )
    parser.add_argument("input", type=Path, help="input VFJ file")
    parser.add_argument("output", type=Path, help="output VFJ file")
    parser.add_argument(
        "-a",
        "--angle",
        type=float,
        required=True,
        help="the slant angle (in degrees)",
    )
    parser.add_argument(
        "-x",
        "--x-offset",
        type=int,
        default=0,
        help="the X offset (default: 0)",
    )
    parser.add_argument(
        "-y",
        "--y-offset",
        type=int,
        default=0,
        help="the Y offset (default: 0)",
    )

    options = parser.parse_args(args)

    font = Font(options.input)

    transform = Identity.skew(options.angle * math.pi / 180)
    if options.x_offset or options.y_offset:
        transform = transform.translate(options.x_offset, options.y_offset)
    process(font, transform)

    font.save(options.output)


if __name__ == "__main__":
    sys.exit(main())
