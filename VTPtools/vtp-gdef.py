import argparse
import logging
import sys

from fontTools.ttLib import TTFont, TTLibError
from fontTools.voltLib.parser import Parser
from fontTools.voltLib import ast
from io import StringIO

log = logging.getLogger()


GDEF_CLASSES = ["base", "ligature", "mark", "component"]


def parsegdef(filepath):
    """Parse into a dictionary a file in the following format:
    # class1
    glyph1
    glyph2
    # class2
    glyph3
    glyph4
    """
    with open(filepath, "r") as f:
        lines = f.readlines()

    gdef = {}
    gtype = None
    for line in lines:
        line = line.strip()
        if line.startswith("#"):
            gtype = line[1:].strip()
            if gtype not in GDEF_CLASSES:
                raise KeyError(
                    f"Unknown glyph class “{gtype}”, must be one of: "
                    f"{', '.join(GDEF_CLASSES)}"
                )
        elif not gtype:
            raise ValueError(f"A glyph class must be dfined before the first glyph")
        else:
            gname = line.split()
            if len(gname) == 2 and gtype == "ligature" and gname[1].isdigit():
                gname, components = gname
                gdef[gname] = [gtype, components]
            elif len(gname) != 1:
                raise ValueError(
                    f"Glyph name “{line}” is not valid, must be a single word"
                )
            else:
                gname = gname[0]
                gdef[gname] = [gtype]

    return gdef


def setgdef(vtp, gdef, missing):
    for statement in vtp.statements:
        if isinstance(statement, ast.GlyphDefinition):
            if statement.name in gdef:
                statement.type = gdef[statement.name][0].upper()
                if len(gdef[statement.name]) == 2:
                    statement.components = int(gdef[statement.name][1])
            elif missing != "keep":
                statement.type = missing.upper()

    return str(vtp)


def main(args=None):
    parser = argparse.ArgumentParser(
        description="Set GDEF glyph classes in VOLT/VTP files."
    )
    parser.add_argument("input", metavar="INPUT", help="input font/VTP file to process")
    parser.add_argument(
        "gdef", metavar="GDEF", help="input GDEF glyph class definition file"
    )
    parser.add_argument("output", metavar="OUTPUT", help="output font/VTP file")
    parser.add_argument(
        "-m",
        "--missing",
        default="base",
        choices=GDEF_CLASSES + ["keep"],
        help="glyph class for glyphs missing from GDEF file, "
        "set to “keep” to leave them unchanged. Default is “base”.",
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

    gdef = parsegdef(options.gdef)
    vtp = Parser(StringIO(indata)).parse()

    outdata = setgdef(vtp, gdef, options.missing)

    if font is not None:
        font["TSIV"].data = outdata.encode("utf-8")
        font.save(options.output)
    else:
        with open(options.output, "w", newline="\r") as f:
            f.write(outdata)


if __name__ == "__main__":
    sys.exit(main())
