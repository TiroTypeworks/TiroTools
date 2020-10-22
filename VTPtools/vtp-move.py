import argparse
import csv
import logging
import sys

from fontTools.misc.fixedTools import otRound
from fontTools.misc.transform import Identity
from fontTools.ttLib import TTFont, TTLibError
from fontTools.voltLib import ast
from fontTools.voltLib.parser import Parser
from io import StringIO
from pathlib import Path

log = logging.getLogger()


def move(pos, xoff, yoff):
    return ast.Pos(
        pos.adv,
        pos.dx + xoff,
        pos.dy + yoff,
        pos.adv_adjust_by,
        pos.dx_adjust_by,
        pos.dy_adjust_by,
    )


def process(data, positions):
    volt = Parser(StringIO(data)).parse()

    offsets = {}
    for anchor in volt.statements:
        if not isinstance(anchor, ast.AnchorDefinition):
            continue
        if not anchor.name.startswith("MARK_"):
            continue

        name = anchor.name.split("_", 1)[1]

        if name not in positions:
            continue

        dx, dy = positions[name]
        xoff, yoff = dx - anchor.pos.dx, dy - anchor.pos.dy
        anchor.pos = move(anchor.pos, xoff, yoff)

        if name not in offsets:
            offsets[name] = (xoff, yoff)

    for anchor in volt.statements:
        if not isinstance(anchor, ast.AnchorDefinition):
            continue
        if anchor.name not in offsets:
            continue

        xoff, yoff = offsets[anchor.name]
        anchor.pos = move(anchor.pos, xoff, yoff)

    return str(volt)


def main(args=None):
    parser = argparse.ArgumentParser(
        description="Move anchor to new positions in VOLT/VTP files."
    )
    parser.add_argument(
        "input", type=Path, metavar="INPUT", help="input font/VTP file to process"
    )
    parser.add_argument(
        "output", type=Path, metavar="OUTPUT", help="output font/VTP file"
    )
    parser.add_argument(
        "-p",
        "--positions",
        type=Path,
        required=True,
        help="CSV file with new anchor positions",
    )

    options = parser.parse_args(args)

    font = None
    try:
        font = TTFont(options.input)
        if "TSIV" in font:
            indata = font["TSIV"].data.decode("utf-8")
        else:
            log.error('"TSIV" table is missing, font was not saved from VOLT?')
            return 1
    except TTLibError:
        with open(options.input) as f:
            indata = f.read()

    with open(options.positions) as f:
        reader = csv.reader(f)
        positions = {row[0]: (int(row[1]), int(row[2])) for row in reader}

    outdata = process(indata, positions)

    if font is not None:
        font["TSIV"].data = outdata.encode("utf-8")
        font.save(options.output)
    else:
        with open(options.output, "w") as f:
            f.write(outdata)


if __name__ == "__main__":
    sys.exit(main())
