import argparse
import sys

from pathlib import Path
from vfj import Font

from fontTools.misc.fixedTools import otRound
from fontTools.voltLib import ast


def _lookup(name):
    return ast.LookupDefinition(
        name,
        True,
        True,
        None,
        'LTR',
        False,
        None,
        None,
        None,
        ast.PositionAttachDefinition(set(), []),
    )


def exportVoltAnchors(font):
    glyphOrder = [g.name for g in font]

    # Save groups and lookups files for each master.
    for master in font.masters:
        # Collect anchors that need mkmk lookups (base glyph is a mark).
        mkmk = set()
        for glyph in font:
            layer = glyph.layers[master.name]
            for anchor in layer.anchors:
                name = anchor.name
                if not name.startswith('_') and glyph.openTypeGlyphClass == 3:
                    mkmk.add(name.split('_')[0])

        lookups = {}
        groups = {}
        anchors = []
        for glyph in font:
            layer = glyph.layers[master.name]
            for anchor in layer.anchors:
                x = otRound(anchor.x)
                y = otRound(anchor.y)
                if anchor.name.startswith('_'):
                    # Mark anchor.
                    if glyph.openTypeGlyphClass != 3:
                        # Not a mark glyph? Ignore the anchor or VOLT will error.
                        continue

                    name = anchor.name[1:]

                    # Add to groups. We build groups for mark glyphs by anchor.
                    group = f'MARK_{name}'
                    if group not in groups:
                        groups[group] = set()
                    groups[group].add(glyph.name)

                    # mkmk anchors are added to both mark and mkmk lookups
                    # because they might be use with non-mark bases after
                    # anchor propagation.
                    lookupnames = [fr'mark\{name}']
                    if name in mkmk:
                        lookupnames.append(fr'mkmk\{name}')

                    # Add the glyph to respective lookup(s).
                    for lookupname in lookupnames:
                        if lookupname not in lookups:
                            lookups[lookupname] = _lookup(lookupname)

                        # For mkmk lookups we use individual glyphs, for mark
                        # lookups we use groups. There is no technical reason
                        # for this, just how JH likes it.
                        if lookupname.startswith('mkmk'):
                            to = ([ast.GlyphName(glyph.name)], name)
                            lookups[lookupname].pos.coverage_to.append(to)
                        elif not lookups[lookupname].pos.coverage_to:
                            to = ([ast.GroupName(group, None)], name)
                            lookups[lookupname].pos.coverage_to.append(to)

                    # Add the anchor.
                    name, comp = f'MARK_{name}', 1
                    pos = ast.Pos(None, x, y, {}, {}, {})
                    gid = glyphOrder.index(glyph.name)
                    anchors.append(
                        ast.AnchorDefinition(name, gid, glyph.name, comp, False, pos)
                    )
                else:
                    # Base anchor.
                    name, comp = anchor.name, 1
                    if '_' in name:
                        # Split ligature anchor (e.g. “top_1” and use the
                        # number for ligature component.
                        name, comp = name.split('_')

                    lookupname = fr'mark\{name}'
                    if glyph.openTypeGlyphClass == 3:
                        # If this is a mark glyph, then add to mkmk lookup.
                        lookupname = fr'mkmk\{name}'

                    # Add the glyph to respective lookup.
                    if lookupname not in lookups:
                        lookups[lookupname] = _lookup(lookupname)
                    lookups[lookupname].pos.coverage.add(glyph.name)

                    # Add the anchor.
                    pos = ast.Pos(None, x, y, {}, {}, {})
                    gid = glyphOrder.index(glyph.name)
                    anchors.append(
                        ast.AnchorDefinition(name, gid, glyph.name, comp, False, pos)
                    )

        # Save groups file.
        with open(master.psn + '.vtg', 'w') as fp:
            doc = ast.VoltFile()
            for group in groups:
                glyphs = tuple(ast.GlyphName(g) for g in sorted(groups[group]))
                enum = ast.Enum(glyphs)
                doc.statements.append(ast.GroupDefinition(group, enum))
            fp.write(str(doc))

        # Save lookups file.
        with open(master.psn + '.vtl', 'w') as fp:
            doc = ast.VoltFile()
            for lookup in lookups.values():
                # Sort coverage by glyph ID to be stable.
                lookup.pos.coverage = sorted(
                    [ast.GlyphName(g) for g in lookup.pos.coverage],
                    key=lambda g: glyphOrder.index(g.glyph),
                )
                doc.statements.append(lookup)
            doc.statements += anchors
            fp.write(str(doc))


def main(args=None):
    parser = argparse.ArgumentParser(
        description="Export VOLT data from FontLab VFJ files."
    )
    parser.add_argument("input", type=Path, help="input VFJ file")
    parser.add_argument(
        "-a",
        "--anchors",
        action='store_true',
        help="write VOLT anchors and glyph groups",
    )

    options = parser.parse_args(args)
    font = Font(options.input)
    if options.anchors:
        exportVoltAnchors(font)


if __name__ == "__main__":
    sys.exit(main())
