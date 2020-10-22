import argparse
import logging
import math
import re
import sys

from fontTools.misc.fixedTools import otRound
from fontTools.misc.transform import Identity
from fontTools.ttLib import TTFont, TTLibError
from fontTools.voltLib.parser import Parser
from io import StringIO

log = logging.getLogger()
anchor_re = re.compile(r"DEF_ANCHOR.*.END_ANCHOR")


def replace(match, transform):
    volt = Parser(StringIO(match.group(0))).parse()
    anchor = volt.statements[0]
    adv, dx, dy, adv_adjust_by, dx_adjust_by, dy_adjust_by = anchor.pos
    if dy:
        dx, dy = transform.transformPoint((dx or 0, dy))

        pos = ""
        if adv is not None:
            pos += " ADV %g" % otRound(adv)
            for at, adjust_by in adv_adjust_by.items():
                pos += f" ADJUST_BY {adjust_by} AT {at}"
        if dx is not None:
            pos += " DX %g" % otRound(dx)
            for at, adjust_by in dx_adjust_by.items():
                pos += f" ADJUST_BY {adjust_by} AT {at}"
        if dy is not None:
            pos += " DY %g" % otRound(dy)
            for at, adjust_by in dy_adjust_by.items():
                pos += f" ADJUST_BY {adjust_by} AT {at}"

        return (
            f'DEF_ANCHOR "{anchor.name}" '
            f"ON {anchor.gid} "
            f"GLYPH {anchor.glyph_name} "
            f"COMPONENT {anchor.component} "
            f'{anchor.locked and "LOCKED " or ""}'
            f"AT  "
            f"POS{pos} END_POS "
            f"END_ANCHOR"
        )
    return match.group(0)


def main(args=None):
    parser = argparse.ArgumentParser(
        description="Transform X anchor positions in VOLT/VTP files."
    )
    parser.add_argument("input", metavar="INPUT", help="input font/VTP file to process")
    parser.add_argument("output", metavar="OUTPUT", help="output font/VTP file")
    parser.add_argument(
        "-a", "--angle", type=float, required=True, help="the slant angle (in degrees)"
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

    transform = Identity.skew(options.angle * math.pi / 180)
    outdata = anchor_re.sub(lambda m: replace(m, transform), indata)

    if font is not None:
        font["TSIV"].data = outdata.encode("utf-8")
        font.save(options.output)
    else:
        with open(options.output, "w") as f:
            f.write(outdata)


if __name__ == "__main__":
    sys.exit(main())
