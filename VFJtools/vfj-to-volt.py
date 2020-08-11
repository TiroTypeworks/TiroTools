#!/usr/bin/env python3
import argparse
import sys
import logging

from pathlib import Path
from vfj import Font

from fontTools.misc.fixedTools import otRound
from fontTools.voltLib import ast


def _pair_lookup(name):
    return ast.LookupDefinition(
        name,
        True,
        False,
        None,
        'LTR',
        False,
        None,
        None,
        None,
        ast.PositionAdjustPairDefinition([], [], {}),
    )


def _attachment_lookup(name):
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
                    lookupnames = [fr'mark_{name}']
                    if name in mkmk:
                        lookupnames.append(fr'mkmk_{name}')

                    # Add the glyph to respective lookup(s).
                    for lookupname in lookupnames:
                        if lookupname not in lookups:
                            lookups[lookupname] = _attachment_lookup(lookupname)

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

                    lookupname = fr'mark_{name}'
                    if glyph.openTypeGlyphClass == 3:
                        # If this is a mark glyph, then add to mkmk lookup.
                        lookupname = fr'mkmk_{name}'

                    # Add the glyph to respective lookup.
                    if lookupname not in lookups:
                        lookups[lookupname] = _attachment_lookup(lookupname)
                    lookups[lookupname].pos.coverage.add(glyph.name)

                    # Add the anchor.
                    pos = ast.Pos(None, x, y, {}, {}, {})
                    gid = glyphOrder.index(glyph.name)
                    anchors.append(
                        ast.AnchorDefinition(name, gid, glyph.name, comp, False, pos)
                    )

        # Save groups file.
        with open(master.psn + '-anchors.vtg', 'w') as fp:
            doc = ast.VoltFile()
            for group in groups:
                glyphs = tuple(ast.GlyphName(g) for g in sorted(groups[group]))
                enum = ast.Enum(glyphs)
                doc.statements.append(ast.GroupDefinition(group, enum))
            fp.write(str(doc))

        # Save lookups file.
        with open(master.psn + '-anchors.vtl', 'w') as fp:
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


def _kern_coverage(names, classes=None):
    ret = []
    for name in names:
        if name.startswith('@'):
            name = name[1:]
            if classes is not None:
                glyphs = tuple(ast.GlyphName(g) for g in sorted(classes[name]))
                ret.append([ast.Enum(glyphs)])
            else:
                ret.append([ast.GroupName(f'KERN{name}', None)])
        else:
            ret.append([ast.GlyphName(name)])
    return ret


def _warn_overlapping_classes(master, groups):
    overlapping = {}
    for class1 in master.kerning.classes:
        if class1.name not in groups:
            continue
        names1 = set(class1.names)
        for class2 in master.kerning.classes:
            if (
                class2.name not in groups
                or class2 == class1
                or class2.first != class1.first
            ):
                continue
            names2 = set(class2.names)
            duplicates = names1.intersection(names2)
            if duplicates:
                key = tuple(sorted([class1.name, class2.name]))
                if key not in overlapping:
                    overlapping[key] = duplicates

    for (name1, name2), duplicates in overlapping.items():
        logging.warning(
            f'Kerning classes {name1} and {name2} overlap in {master.name}:\n'
            f'{", ".join(sorted(duplicates))}\n'
        )


def exportVoltKerning(font):
    # Save groups and lookups files for each master.
    for master in font.masters:
        classes = {k.name: k.names for k in master.kerning.classes}
        pairs = master.kerning.pairs.copy()

        format1 = _pair_lookup(r'kern\1_PPF1')
        format2 = _pair_lookup(r'kern\2_PPF2')
        nullpos = ast.Pos(None, None, None, {}, {}, {})

        # Left exceptions
        filtered = {}
        for left in pairs:
            if left.startswith('@'):
                names = []
                for name in classes[left[1:]]:
                    if name in pairs:
                        pairs[name] = {**pairs[left], **pairs[name]}
                    else:
                        names.append(name)
                filtered[left[1:]] = names

        # Right exceptions
        rights = set()
        for left in pairs:
            rights.update(pairs[left])

        for right in sorted(rights):
            if right.startswith('@'):
                names = []
                for name in classes[right[1:]]:
                    if name in rights:
                        for left in pairs:
                            if right in pairs[left]:
                                pairs[left][name] = pairs[left][right]
                    else:
                        names.append(name)
                filtered[right[1:]] = names

        groups = set()
        values = {}
        for left in pairs:
            for right, value in pairs[left].items():
                lookup = format1
                if left.startswith('@') and right.startswith('@'):
                    lookup = format2
                    groups.update([left[1:], right[1:]])
                else:
                    if left.startswith('@') and not filtered[left[1:]]:
                        continue
                    if right.startswith('@') and not filtered[right[1:]]:
                        continue

                if left not in lookup.pos.coverages_1:
                    lookup.pos.coverages_1.append(left)
                id1 = lookup.pos.coverages_1.index(left) + 1

                if right not in lookup.pos.coverages_2:
                    lookup.pos.coverages_2.append(right)
                id2 = lookup.pos.coverages_2.index(right) + 1

                pos = ast.Pos(otRound(value), None, None, {}, {}, {})
                lookup.pos.adjust_pair[(id1, id2)] = (pos, nullpos)

        _warn_overlapping_classes(master, groups)

        # Save groups file.
        with open(master.psn + '-kerning.vtg', 'w') as fp:
            doc = ast.VoltFile()
            for name in sorted(groups):
                glyphs = tuple(ast.GlyphName(g) for g in sorted(classes[name]))
                enum = ast.Enum(glyphs)
                doc.statements.append(ast.GroupDefinition(f'KERN{name}', enum))
            fp.write(str(doc))

        # Save lookups file.
        with open(master.psn + '-kerning.vtl', 'w') as fp:
            format1.pos.coverages_1 = _kern_coverage(format1.pos.coverages_1, filtered)
            format1.pos.coverages_2 = _kern_coverage(format1.pos.coverages_2, filtered)

            format2.pos.coverages_1 = _kern_coverage(format2.pos.coverages_1)
            format2.pos.coverages_2 = _kern_coverage(format2.pos.coverages_2)

            doc = ast.VoltFile()
            doc.statements = [format1, format2]
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
    parser.add_argument(
        "-k",
        "--kerning",
        action='store_true',
        help="write VOLT kerning and glyph groups",
    )

    options = parser.parse_args(args)
    font = Font(options.input)
    if options.anchors:
        exportVoltAnchors(font)
    if options.kerning:
        exportVoltKerning(font)


if __name__ == "__main__":
    sys.exit(main())
