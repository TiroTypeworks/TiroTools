#!/usr/bin/env python3
import argparse
import sys
import logging

from pathlib import Path
from vfj import Font

from fontTools.misc.fixedTools import otRound
from fontTools.voltLib import ast


def _attachment_lookup(name):
    return ast.LookupDefinition(
        name,
        True,
        True,
        None,
        "LTR",
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
                if not name.startswith("_") and glyph.openTypeGlyphClass == 3:
                    mkmk.add(name.split("_")[0])

        # Collect anchors that need ligature lookups (anchor with index).
        ligs = set()
        for glyph in font:
            layer = glyph.layers[master.name]
            for anchor in layer.anchors:
                name = anchor.name
                if name.startswith("_"):
                    name = name[1:]
                if "_" in name:
                    ligs.add(name.split("_")[0])

        lookups = {}
        groups = {}
        anchors = []
        for glyph in font:
            layer = glyph.layers[master.name]
            for anchor in layer.anchors:
                x = otRound(anchor.x)
                y = otRound(anchor.y)
                if anchor.name.startswith("_"):
                    # Mark anchor.
                    if glyph.openTypeGlyphClass != 3:
                        # Not a mark glyph? Ignore the anchor or VOLT will error.
                        continue

                    name = anchor.name[1:]

                    # Add to groups. We build groups for mark glyphs by anchor.
                    group = f"MARK_{name}"
                    if group not in groups:
                        groups[group] = set()
                    groups[group].add(glyph.name)

                    # mkmk anchors are added to both mark and mkmk lookups
                    # because they might be used with non-mark bases after
                    # anchor propagation.
                    lookupnames = [f"mark_{name}"]
                    if name in mkmk:
                        lookupnames.append(f"mkmk_{name}")
                    if name in ligs:
                        lookupnames.append(f"mark_{name}_ligs")

                    # Add the glyph to respective lookup(s).
                    for lookupname in lookupnames:
                        if lookupname not in lookups:
                            lookups[lookupname] = _attachment_lookup(lookupname)

                        # For mkmk lookups we use individual glyphs, for mark
                        # lookups we use groups. There is no technical reason
                        # for this, just how JH likes it.
                        if lookupname.startswith("mkmk"):
                            to = ([ast.GlyphName(glyph.name)], name)
                            lookups[lookupname].pos.coverage_to.append(to)
                        elif not lookups[lookupname].pos.coverage_to:
                            to = ([ast.GroupName(group, None)], name)
                            lookups[lookupname].pos.coverage_to.append(to)

                    # Add the anchor.
                    name, comp = f"MARK_{name}", 1
                    pos = ast.Pos(None, x, y, {}, {}, {})
                    gid = glyphOrder.index(glyph.name)
                    anchors.append(
                        ast.AnchorDefinition(name, gid, glyph.name, comp, False, pos)
                    )
                else:
                    # Base anchor.
                    name, comp = anchor.name, 1
                    lookupname = f"mark_{name}"
                    if "_" in name:
                        # Split ligature anchor (e.g. “top_1” and use the
                        # number for ligature component.
                        name, comp = name.split("_")
                        lookupname = f"mark_{name}_ligs"

                    if glyph.openTypeGlyphClass == 3:
                        # If this is a mark glyph, then add to mkmk lookup.
                        lookupname = f"mkmk_{name}"

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
        with open(master.psn + "-anchors.vtg", "w") as fp:
            doc = ast.VoltFile()
            for group in groups:
                glyphs = tuple(ast.GlyphName(g) for g in sorted(groups[group]))
                enum = ast.Enum(glyphs)
                doc.statements.append(ast.GroupDefinition(group, enum))
            fp.write(str(doc))

        # Save lookups file.
        with open(master.psn + "-anchors.vtl", "w") as fp:
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


def _kern_group_name(name):
    if not name.startswith("KERN"):
        name = "KERN" + name
    return name


def _kern_coverage(names):
    ret = []
    for name in names:
        if name.startswith("@"):
            ret.append([ast.GroupName(_kern_group_name(name[1:]), None)])
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
            f"Kerning classes {name1} and {name2} overlap in {master.name}:\n"
            f'{", ".join(sorted(duplicates))}\n'
        )


def _sart_pair_lookup(lookups, kind="PPF1"):
    name = rf"kern\{len(lookups) + 1}_{kind}"
    lookup = ast.LookupDefinition(
        name,
        True,
        False,
        None,
        "LTR",
        False,
        None,
        None,
        None,
        ast.PositionAdjustPairDefinition([], [], {}),
    )
    lookup.vfj_len = 0
    lookups.append(lookup)


nullpos = ast.Pos(None, None, None, {}, {}, {})


def _pair_len(left, right, classes):
    if left.startswith("@") and right.startswith("@"):
        return 1
    if left.startswith("@"):
        return len(classes[left[1:]])
    if right.startswith("@"):
        return len(classes[right[1:]])
    return 1


def _kern_pair(lookups, left, right, value, max_pairs=None, classes=[]):
    if max_pairs:
        pair_len = _pair_len(left, right, classes)
        if lookups[-1].vfj_len + pair_len > max_pairs:
            # If the number of pairs exceeds the max, start a new lookup
            # subtable.
            kind = lookups[-1].name.rsplit("_", 1)[1]
            _sart_pair_lookup(lookups, kind)

    lookup = lookups[-1]
    if left not in lookup.pos.coverages_1:
        lookup.pos.coverages_1.append(left)
    id1 = lookup.pos.coverages_1.index(left) + 1

    if right not in lookup.pos.coverages_2:
        lookup.pos.coverages_2.append(right)
    id2 = lookup.pos.coverages_2.index(right) + 1

    pos = ast.Pos(value, None, None, {}, {}, {})
    lookup.pos.adjust_pair[(id1, id2)] = (pos, nullpos)

    if max_pairs:
        lookup.vfj_len += pair_len


def exportVoltKerning(font, max_pairs):
    # Save groups and lookups files for each master.
    for master in font.masters:
        classes = {k.name: k.names for k in master.kerning.classes}

        # Get kerning pairs as a flat list.
        pairs = []
        for left in master.kerning.pairs:
            for right, value in master.kerning.pairs[left].items():
                if ";" in value:
                    # This seems to be the Flag color applied to the pair in FL UI.
                    value = value.split(";")[0]
                pairs.append(((left, right), otRound(float(value))))

        lookups = []

        # Write format 1 lookup for individual glyph pairs first.
        _sart_pair_lookup(lookups)
        for (left, right), value in pairs:
            if not left.startswith("@") and not right.startswith("@"):
                _kern_pair(lookups, left, right, value, max_pairs, classes)

        # Then write format 1 lookup for pairs where right side is a class.
        _sart_pair_lookup(lookups)
        for (left, right), value in pairs:
            if not left.startswith("@") and right.startswith("@"):
                _kern_pair(lookups, left, right, value, max_pairs, classes)

        # Then write format 1 lookup for pairs where left side is a class.
        _sart_pair_lookup(lookups)
        for (left, right), value in pairs:
            if left.startswith("@") and not right.startswith("@"):
                _kern_pair(lookups, left, right, value, max_pairs, classes)

        # Lastly write format 2 (class kerning).
        _sart_pair_lookup(lookups, "PPF2")
        for (left, right), value in pairs:
            if left.startswith("@") and right.startswith("@"):
                _kern_pair(lookups, left, right, value, max_pairs, classes)

        # Collect used groups to avoid writing groups not used in kerning.
        groups = set()
        for (left, right), value in pairs:
            if left.startswith("@"):
                groups.add(left[1:])
            if right.startswith("@"):
                groups.add(right[1:])

        _warn_overlapping_classes(master, groups)

        # Save groups file.
        with open(master.psn + "-kerning.vtg", "w") as fp:
            doc = ast.VoltFile()
            for name in sorted(groups):
                glyphs = tuple(ast.GlyphName(g) for g in sorted(classes[name]))
                enum = ast.Enum(glyphs)
                doc.statements.append(ast.GroupDefinition(_kern_group_name(name), enum))
            fp.write(str(doc))

        # Save lookups file.
        with open(master.psn + "-kerning.vtl", "w") as fp:
            for lookup in lookups:
                lookup.pos.coverages_1 = _kern_coverage(lookup.pos.coverages_1)
                lookup.pos.coverages_2 = _kern_coverage(lookup.pos.coverages_2)

            doc = ast.VoltFile()
            doc.statements = lookups
            fp.write(str(doc))


def main(args=None):
    parser = argparse.ArgumentParser(
        description="Export VOLT data from FontLab VFJ files."
    )
    parser.add_argument("input", type=Path, help="input VFJ file")
    parser.add_argument(
        "-a",
        "--anchors",
        action="store_true",
        help="write VOLT anchors and glyph groups",
    )
    parser.add_argument(
        "-k",
        "--kerning",
        action="store_true",
        help="write VOLT kerning and glyph groups",
    )
    parser.add_argument(
        "-s",
        "--split-kern",
        type=int,
        metavar="N",
        help="split kern subtables after N number of pairs",
    )

    options = parser.parse_args(args)

    font = Font(options.input)
    if options.anchors:
        exportVoltAnchors(font)
    if options.kerning:
        exportVoltKerning(font, options.split_kern)


if __name__ == "__main__":
    sys.exit(main())
