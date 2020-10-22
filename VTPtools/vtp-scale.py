import argparse
import logging
import re
import sys

from fontTools.misc.fixedTools import otRound
from fontTools.ttLib import TTFont, TTLibError
from fontTools.voltLib.parser import Parser
from io import StringIO

log = logging.getLogger()
pos_re = re.compile(r"POS.*?.END_POS")


def replace(match, factor):
    pos = Parser(StringIO(match.group(0))).parse_pos_()

    if not any(pos):
        return match.group(0)

    adv, dx, dy, adv_adjust_by, dx_adjust_by, dy_adjust_by = pos

    ret = ""
    if adv is not None:
        adv = otRound(adv * factor)
        ret += f" ADV {adv:g}"
        for at, adjust_by in adv_adjust_by.items():
            at, adjust_by = otRound(at * factor), otRound(adjust_by * factor)
            ret += f" ADJUST_BY {adjust_by} AT {at}"

    if dx is not None:
        dx = otRound(dx * factor)
        ret += f" DX {dx:g}"
        for at, adjust_by in dx_adjust_by.items():
            at, adjust_by = otRound(at * factor), otRound(adjust_by * factor)
            ret += f" ADJUST_BY {adjust_by} AT {at}"

    if dy is not None:
        dy = otRound(dy * factor)
        ret += f" DY {dy:g}"
        for at, adjust_by in dy_adjust_by.items():
            at, adjust_by = otRound(at * factor), otRound(adjust_by * factor)
            ret += f" ADJUST_BY {adjust_by} AT {at}"

    return f"POS{ret} END_POS"


def main(args=None):
    parser = argparse.ArgumentParser(
        description="Scale positioning data in VOLT/VTP files."
    )
    parser.add_argument("input", metavar="INPUT", help="input font/VTP file to process")
    parser.add_argument("output", metavar="OUTPUT", help="output font/VTP file")
    parser.add_argument(
        "-f", "--factor", type=float, required=True, help="the scale factor"
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

    outdata = pos_re.sub(lambda m: replace(m, options.factor), indata)

    if font is not None:
        font["TSIV"].data = outdata.encode("utf-8")
        font.save(options.output)
    else:
        with open(options.output, "w") as f:
            f.write(outdata)


if __name__ == "__main__":
    sys.exit(main())
