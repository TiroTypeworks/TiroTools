#!/usr/bin/env python3
import argparse
import logging
import sys
from collections import defaultdict
from pathlib import Path

from fontTools.ttLib import TTFont, TTLibError
from fontTools.voltLib import ast
from fontTools.voltLib.parser import Parser
from vfj import Font

log = logging.getLogger()


def convertAnchors(anchors):
    out = defaultdict(list)
    for glyph_name in anchors:
        for anchor_name, glyph_anchors in anchors[glyph_name].items():
            if len(glyph_anchors) == 1:
                x, y, _ = glyph_anchors[0]
                out[glyph_name].append((anchor_name, x, y))
            else:
                for x, y, component in glyph_anchors:
                    out[glyph_name].append((f"{anchor_name}_{component - 1}", x, y))
    return out


def collectAnchors(vtp):
    anchors = defaultdict(lambda: defaultdict(list))

    for statement in vtp.statements:
        if isinstance(statement, ast.AnchorDefinition):
            name = statement.name
            if name.startswith("MARK_"):
                name = name[len("MARK") :]
            pos = statement.pos
            anchors[statement.glyph_name][name].append(
                (
                    pos.dx or 0,
                    pos.dy or 0,
                    statement.component,
                )
            )
    return convertAnchors(anchors)


def copyAnchors(vtp, vfj, layer_name):
    anchors = collectAnchors(vtp)
    for glyph_name in anchors:
        glyph = vfj[glyph_name]
        layer = glyph.layers[layer_name]
        for anchor_name, x, y in anchors[glyph_name]:
            if anchor_name not in layer.anchors:
                layer.anchors.addAnchor(dict(name=anchor_name, point=f"{x} {y}"))
            else:
                anchor = layer.anchors[anchor_name]
                anchor.x = x
                anchor.y = y


def main(args=None):
    parser = argparse.ArgumentParser(
        description="Copy anchors from VTP files to VFJ files."
    )
    parser.add_argument("vtp", type=Path, help="input font/VTP file")
    parser.add_argument("vfj", type=Path, help="input VFJ file")
    parser.add_argument("output", type=Path, help="output VFJ file")
    parser.add_argument(
        "-l",
        "--layer",
        type=str,
        default=None,
        help="VFJ font layer name to copy anchors to, default: first layer",
    )

    options = parser.parse_args(args)

    try:
        ttFont = TTFont(options.vtp)
        if "TSIV" in ttFont:
            from io import StringIO

            vtpData = ttFont["TSIV"].data.decode("utf-8")
            vtp = Parser(StringIO(vtpData)).parse()
        else:
            log.error('"TSIV" table is missing, font was not saved from VOLT?')
            return 1
    except TTLibError:
        vtp = Parser(options.vtp).parse()

    vfj = Font(options.vfj)

    layer = options.layer
    if layer is None:
        layer = vfj.masters[0].name
    else:
        master_names = [m.name for m in vfj.masters]
        if layer not in master_names:
            log.error(f"Layer '{layer}' is not present in VFJ file")
            return 1

    copyAnchors(vtp, vfj, layer)

    vfj.save(options.output)


if __name__ == "__main__":
    sys.exit(main())
