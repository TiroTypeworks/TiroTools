import logging
import re

from collections import OrderedDict
from tempfile import NamedTemporaryFile

from fontTools.ttLib import TTFont, TTLibError
from fontTools.feaLib import ast
from fontTools.voltLib import ast as VAst
from fontTools.voltLib.parser import Parser as VoltParser

log = logging.getLogger()


class MarkClassDefinition(ast.MarkClassDefinition):
    def asFea(self, indent=""):
        res = ""
        if not getattr(self, "used", False):
            res += "#"
        res += ast.MarkClassDefinition.asFea(self, indent)
        return res


class VoltToFea:
    _NOT_LOOKUP_NAME_RE = re.compile(r"[^A-Za-z_0-9.]")
    _NOT_CLASS_NAME_RE = re.compile(r"[^A-Za-z_0-9.\-]")

    def __init__(self, filename):
        self._filename = filename

        self._glyph_map = {}
        self._glyph_order = None

        self._gdef = {}
        self._glyphclasses = OrderedDict()
        self._features = OrderedDict()
        self._lookups = OrderedDict()

        self._marks = set()
        self._ligatures = {}

        self._markclasses = {}
        self._anchors = {}

        self._settings = {}

        self._lookup_names = {}
        self._class_names = {}

    def _lookupName(self, name):
        if name not in self._lookup_names:
            res = self._NOT_LOOKUP_NAME_RE.sub("_", name)
            while res in self._lookup_names.values():
                res += "_"
            self._lookup_names[name] = res
        return self._lookup_names[name]

    def _className(self, name):
        if name not in self._class_names:
            res = self._NOT_CLASS_NAME_RE.sub("_", name)
            while res in self._class_names.values():
                res += "_"
            self._class_names[name] = res
        return self._class_names[name]

    def _parse(self, filename):
        font = None
        try:
            font = TTFont(filename)
            if "TSIV" in font:
                with NamedTemporaryFile() as temp:
                    temp.write(font["TSIV"].data)
                    temp.flush()
                    parser = VoltParser(temp.name)
        except TTLibError:
            parser = VoltParser(filename)

        return parser.parse(), font

    def _collectStatements(self, doc):
        for statement in doc.statements:
            if isinstance(statement, VAst.GlyphDefinition):
                self._glyphDefinition(statement)
            elif isinstance(statement, VAst.AnchorDefinition):
                self._anchorDefinition(statement)
            elif isinstance(statement, VAst.SettingDefinition):
                self._settingDefinition(statement)
            elif isinstance(statement, VAst.GroupDefinition):
                self._groupDefinition(statement)
            elif isinstance(statement, VAst.ScriptDefinition):
                self._scriptDefinition(statement)
            elif not isinstance(statement, VAst.LookupDefinition):
                raise NotImplementedError(statement)

        # Lookup definitions need to be handled last as they reference glyph
        # and mark classes that might be defined after them.
        for statement in doc.statements:
            if isinstance(statement, VAst.LookupDefinition):
                self._lookupDefinition(statement)

    def _buildFeatureFile(self):
        doc = ast.FeatureFile()
        statements = doc.statements

        statements.append(ast.Comment("# Glyph classes"))
        statements.extend(self._glyphclasses.values())

        statements.append(ast.Comment("\n# Mark classes"))
        statements.extend(c[1] for c in sorted(self._markclasses.items()))

        statements.append(ast.Comment("\n# Lookups"))
        # Merge sub lookups (lookups named “base\sub”, but only when they are
        # pairpos lookups as feature files don’t support “subtable” statement
        # for other lookups.
        lookups = OrderedDict()
        for name, lookup in self._lookups.items():
            if "\\" in name and \
                    isinstance(lookup.statements[-1], ast.PairPosStatement):
                base = name.split("\\")[0]
                if base not in lookups:
                    lookups[base] = []
                lookups[base].append(lookup)
            else:
                if "\\" in name:
                    log.warning('Lookup should be a subtable, but feature '
                                'files allow subtables only in pair '
                                'positioning lookups: %s', name)
                lookups[name] = [lookup]

        for name, sublookups in lookups.items():
            if len(sublookups) > 1:
                base = sublookups[0]
                voltname = getattr(base, "voltname", base.name)
                base.statements.insert(0, ast.Comment("# " + voltname))
                base.name = name
                for sublookup in sublookups[1:]:
                    sublookup.merged = True
                    base.statements.append(ast.SubtableStatement())
                    voltname = getattr(sublookup, "voltname", sublookup.name)
                    base.statements.append(ast.Comment("# " + voltname))
                    base.statements.extend(sublookup.statements)
                statements.append(base)
            else:
                statements.extend(sublookups)

        statements.append(ast.Comment("# Features"))
        for ftag, scripts in self._features.items():
            feature = ast.FeatureBlock(ftag)
            stags = sorted(scripts, key=lambda k: 0 if k == "DFLT" else 1)
            for stag in stags:
                script = ast.ScriptStatement(stag)
                langs = scripts[stag]
                feature.statements.append(script)
                for ltag, lookups in langs.items():
                    lang = ast.LanguageStatement(ltag)
                    feature.statements.append(lang)
                    for name in lookups:
                        lookup = self._lookups[name.lower()]
                        if getattr(lookup, "merged", False):
                            continue
                        lookupref = ast.LookupReferenceStatement(lookup)
                        feature.statements.append(lookupref)
            statements.append(feature)

        if self._gdef:
            gdef = ast.TableBlock("GDEF")
            gdef.statements.append(
                ast.GlyphClassDefStatement(self._gdef.get("BASE"),
                                           self._gdef.get("MARK"),
                                           self._gdef.get("LIGATURE"),
                                           self._gdef.get("COMPONENT")))

            statements.append(gdef)

        return doc

    def convert(self, path):
        doc, font = self._parse(self._filename)

        if font is not None:
            self._glyph_order = font.getGlyphOrder()

        self._collectStatements(doc)
        fea = self._buildFeatureFile()

        with open(path, "w") as feafile:
            feafile.write(fea.asFea())

    def _glyphName(self, glyph):
        try:
            name = glyph.glyph
        except AttributeError:
            name = glyph
        return ast.GlyphName(self._glyph_map[name])

    def _groupName(self, group):
        try:
            name = group.group
        except AttributeError:
            name = group
        return ast.GlyphClassName(self._glyphclasses[name.lower()])

    def _coverage(self, coverage):
        items = []
        for item in coverage:
            if isinstance(item, VAst.GlyphName):
                items.append(self._glyphName(item))
            elif isinstance(item, VAst.GroupName):
                items.append(self._groupName(item))
            elif isinstance(item, VAst.Enum):
                items.append(self._enum(item))
            elif isinstance(item, VAst.Range):
                items.append(ast.GlyphClass(item.glyphSet()))
            else:
                raise NotImplementedError(item)
        return items

    def _enum(self, enum):
        return ast.GlyphClass(self._coverage(enum.enum))

    def _context(self, context):
        out = []
        for item in context:
            coverage = self._coverage(item)
            if not isinstance(coverage, (tuple, list)):
                coverage = [coverage]
            out.extend(coverage)
        return out

    def _groupDefinition(self, group):
        name = self._className(group.name)
        glyphs = self._enum(group.enum)
        glyphclass = ast.GlyphClassDefinition(name, glyphs)

        self._glyphclasses[group.name.lower()] = glyphclass

    def _glyphDefinition(self, glyph):
        try:
            self._glyph_map[glyph.name] = self._glyph_order[glyph.id]
        except TypeError:
            self._glyph_map[glyph.name] = glyph.name

        if glyph.type not in self._gdef:
            self._gdef[glyph.type] = ast.GlyphClass()
        self._gdef[glyph.type].glyphs.append(self._glyphName(glyph.name))

        if glyph.type == "MARK":
            self._marks.add(glyph.name)
        elif glyph.type == "LIGATURE":
            self._ligatures[glyph.name] = glyph.components

    def _scriptDefinition(self, script):
        stag = script.tag
        for lang in script.langs:
            ltag = lang.tag
            for feature in lang.features:
                ftag = feature.tag
                if ftag not in self._features:
                    self._features[ftag] = OrderedDict()
                if stag not in self._features[ftag]:
                    self._features[ftag][stag] = OrderedDict()
                assert ltag not in self._features[ftag][stag]
                self._features[ftag][stag][ltag] = feature.lookups

    def _settingDefinition(self, setting):
        if setting.name.startswith("COMPILER_"):
            self._settings[setting.name] = setting.value
        else:
            log.warning("Unsupported setting ignored: %s", setting.name)

    def _adjustment(self, adjustment):
        adv, dx, dy, adv_adjust_by, dx_adjust_by, dy_adjust_by = adjustment

        adv_device = adv_adjust_by and adv_adjust_by.items() or None
        dx_device = dx_adjust_by and dx_adjust_by.items() or None
        dy_device = dy_adjust_by and dy_adjust_by.items() or None

        return ast.ValueRecord(xPlacement=dx, yPlacement=dy, xAdvance=adv,
                               xPlaDevice=dx_device, yPlaDevice=dy_device,
                               xAdvDevice=adv_device)

    def _anchor(self, adjustment):
        adv, dx, dy, adv_adjust_by, dx_adjust_by, dy_adjust_by = adjustment

        assert not adv_adjust_by
        dx_device = dx_adjust_by and dx_adjust_by.items() or None
        dy_device = dy_adjust_by and dy_adjust_by.items() or None

        return ast.Anchor(dx or 0, dy or 0,
                          xDeviceTable=dx_device or None,
                          yDeviceTable=dy_device or None)

    def _anchorDefinition(self, anchordef):
        anchorname = anchordef.name
        glyphname = anchordef.glyph_name
        anchor = self._anchor(anchordef.pos)

        if anchorname.startswith("MARK_"):
            name = "_".join(anchorname.split("_")[1:])
            markclass = ast.MarkClass(self._className(name))
            glyph = self._glyphName(glyphname)
            markdef = MarkClassDefinition(markclass, anchor, glyph)
            self._markclasses[(glyphname, anchorname)] = markdef
        else:
            if glyphname not in self._anchors:
                self._anchors[glyphname] = {}
            if anchorname not in self._anchors[glyphname]:
                self._anchors[glyphname][anchorname] = {}
            self._anchors[glyphname][anchorname][anchordef.component] = anchor

    def _gposLookup(self, lookup, fealookup):
        statements = fealookup.statements

        pos = lookup.pos
        if isinstance(pos, VAst.PositionAdjustPairDefinition):
            for (idx1, idx2), (pos1, pos2) in pos.adjust_pair.items():
                coverage_1 = pos.coverages_1[idx1 - 1]
                coverage_2 = pos.coverages_2[idx2 - 1]

                # If not both are groups, use “enum pos” otherwise makeotf will
                # fail.
                enumerated = False
                for item in coverage_1 + coverage_2:
                    if not isinstance(item, VAst.GroupName):
                        enumerated = True

                glyphs1 = self._coverage(coverage_1)
                glyphs2 = self._coverage(coverage_2)
                record1 = self._adjustment(pos1)
                record2 = self._adjustment(pos2)
                assert len(glyphs1) == 1
                assert len(glyphs2) == 1
                statements.append(ast.PairPosStatement(
                    glyphs1[0], record1, glyphs2[0], record2,
                    enumerated=enumerated))
        elif isinstance(pos, VAst.PositionAdjustSingleDefinition):
            for a, b in pos.adjust_single:
                glyphs = self._coverage(a)
                record = self._adjustment(b)
                assert len(glyphs) == 1
                statements.append(ast.SinglePosStatement(
                    [(glyphs[0], record)], [], [], False))
        elif isinstance(pos, VAst.PositionAttachDefinition):
            anchors = {}
            for marks, classname in pos.coverage_to:
                for mark in marks:
                    # Set actually used mark classes. Basically a hack to get
                    # around the feature file syntax limitation of making mark
                    # classes global and not allowing mark positioning to
                    # specify mark coverage.
                    for name in mark.glyphSet():
                        key = (name, "MARK_" + classname)
                        self._markclasses[key].used = True
                markclass = ast.MarkClass(self._className(classname))
                for base in pos.coverage:
                    for name in base.glyphSet():
                        if name not in anchors:
                            anchors[name] = []
                        if classname not in anchors[name]:
                            anchors[name].append(classname)

            for name in anchors:
                components = 1
                if name in self._ligatures:
                    components = self._ligatures[name]

                marks = []
                for mark in anchors[name]:
                    markclass = ast.MarkClass(self._className(mark))
                    for component in range(1, components + 1):
                        if len(marks) < component:
                            marks.append([])
                        anchor = None
                        if component in self._anchors[name][mark]:
                            anchor = self._anchors[name][mark][component]
                        marks[component - 1].append((anchor, markclass))

                base = self._glyphName(name)
                if name in self._marks:
                    mark = ast.MarkMarkPosStatement(base, marks[0])
                elif name in self._ligatures:
                    mark = ast.MarkLigPosStatement(base, marks)
                else:
                    mark = ast.MarkBasePosStatement(base, marks[0])
                statements.append(mark)
        elif isinstance(pos, VAst.PositionAttachCursiveDefinition):
            # Collect enter and exit glyphs
            enter_coverage = []
            for coverage in pos.coverages_enter:
                for base in coverage:
                    for name in base.glyphSet():
                        enter_coverage.append(name)
            exit_coverage = []
            for coverage in pos.coverages_exit:
                for base in coverage:
                    for name in base.glyphSet():
                        exit_coverage.append(name)

            # Write enter anchors, also check if the glyph has exit anchor and
            # write it, too.
            for name in enter_coverage:
                glyph = self._glyphName(name)
                entry = self._anchors[name]["entry"][1]
                exit = None
                if name in exit_coverage:
                    exit = self._anchors[name]["exit"][1]
                    exit_coverage.pop(exit_coverage.index(name))
                statements.append(ast.CursivePosStatement(glyph, entry, exit))

            # Write any remaining exit anchors.
            for name in exit_coverage:
                glyph = self._glyphName(name)
                exit = self._anchors[name]["exit"][1]
                statements.append(ast.CursivePosStatement(glyph, None, exit))
        else:
            raise NotImplementedError(pos)

    def _gposContextLookup(self, lookup, prefix, suffix, ignore, fealookup,
                           targetlookup):
        statements = fealookup.statements

        assert not lookup.reversal

        pos = lookup.pos
        if isinstance(pos, VAst.PositionAdjustPairDefinition):
            for (idx1, idx2), (pos1, pos2) in pos.adjust_pair.items():
                glyphs1 = self._coverage(pos.coverages_1[idx1 - 1])
                glyphs2 = self._coverage(pos.coverages_2[idx2 - 1])
                assert len(glyphs1) == 1
                assert len(glyphs2) == 1
                glyphs = (glyphs1[0], glyphs2[0])

                if ignore:
                    statement = ast.IgnorePosStatement(
                        [(prefix, glyphs, suffix)])
                else:
                    lookups = (targetlookup, targetlookup)
                    statement = ast.ChainContextPosStatement(
                        prefix, glyphs, suffix, lookups)
                statements.append(statement)
        elif isinstance(pos, VAst.PositionAdjustSingleDefinition):
            glyphs = [ast.GlyphClass()]
            for a, b in pos.adjust_single:
                glyph = self._coverage(a)
                glyphs[0].extend(glyph)

            if ignore:
                statement = ast.IgnorePosStatement([(prefix, glyphs, suffix)])
            else:
                statement = ast.ChainContextPosStatement(
                    prefix, glyphs, suffix, [targetlookup])
            statements.append(statement)
        elif isinstance(pos, VAst.PositionAttachDefinition):
            glyphs = [ast.GlyphClass()]
            for coverage, _ in pos.coverage_to:
                glyphs[0].extend(self._coverage(coverage))

            if ignore:
                statement = ast.IgnorePosStatement([(prefix, glyphs, suffix)])
            else:
                statement = ast.ChainContextPosStatement(
                    prefix, glyphs, suffix, [targetlookup])
            statements.append(statement)
        else:
            raise NotImplementedError(pos)

    def _gsubLookup(self, lookup, prefix, suffix, ignore, chain, fealookup):
        statements = fealookup.statements

        sub = lookup.sub
        for key, val in sub.mapping.items():
            if not key or not val:
                path, line, column = sub.location
                log.warning("%s:%d:%d: Ignoring empty substitution",
                            path, line, column)
                continue
            statement = None
            glyphs = self._coverage(key)
            replacements = self._coverage(val)
            if ignore:
                chain_context = (prefix, glyphs, suffix)
                statement = ast.IgnoreSubstStatement([chain_context])
            elif isinstance(sub, VAst.SubstitutionSingleDefinition):
                assert(len(glyphs) == 1)
                assert(len(replacements) == 1)
                statement = ast.SingleSubstStatement(
                    glyphs, replacements, prefix, suffix, chain)
            elif isinstance(sub,
                            VAst.SubstitutionReverseChainingSingleDefinition):
                assert(len(glyphs) == 1)
                assert(len(replacements) == 1)
                statement = ast.ReverseChainSingleSubstStatement(
                    prefix, suffix, glyphs, replacements)
            elif isinstance(sub, VAst.SubstitutionMultipleDefinition):
                assert(len(glyphs) == 1)
                statement = ast.MultipleSubstStatement(
                    prefix, glyphs[0], suffix, replacements, chain)
            elif isinstance(sub, VAst.SubstitutionLigatureDefinition):
                assert(len(replacements) == 1)
                statement = ast.LigatureSubstStatement(
                    prefix, glyphs, suffix, replacements[0], chain)
            else:
                raise NotImplementedError(sub)
            statements.append(statement)

    def _lookupDefinition(self, lookup):
        mark_attachement = None
        mark_filtering = None

        flags = 0
        if lookup.direction == "RTL":
            flags |= 1
        if not lookup.process_base:
            flags |= 2
        # FIXME: Does VOLT support this?
        # if not lookup.process_ligatures:
        #     flags |= 4
        if not lookup.process_marks:
            flags |= 8
        elif isinstance(lookup.process_marks, str):
            mark_attachement = self._groupName(lookup.process_marks)
        elif lookup.mark_glyph_set is not None:
            mark_filtering = self._groupName(lookup.mark_glyph_set)

        fealookup = ast.LookupBlock(self._lookupName(lookup.name))
        fealookup.voltname = lookup.name

        if lookup.comments is not None:
            fealookup.statements.append(ast.Comment(lookup.comments))

        if flags or mark_attachement is not None or mark_filtering is not None:
            lookupflags = ast.LookupFlagStatement(flags, mark_attachement,
                                                  mark_filtering)
            fealookup.statements.append(lookupflags)

        contexts = []
        if lookup.context:
            for context in lookup.context:
                prefix = self._context(context.left)
                suffix = self._context(context.right)
                ignore = context.ex_or_in == "EXCEPT_CONTEXT"
                contexts.append([prefix, suffix, ignore, False])
                # It seems that VOLT will create contextual substitution using
                # only the input if there is no other contexts in this lookup.
                if ignore and len(lookup.context) == 1:
                    contexts.append([[], [], False, True])
        else:
            contexts.append([[], [], False, False])

        targetlookup = None
        for prefix, suffix, ignore, chain in contexts:
            if lookup.sub is not None:
                self._gsubLookup(lookup, prefix, suffix, ignore, chain,
                                 fealookup)

            if lookup.pos is not None:
                if self._settings.get("COMPILER_USEEXTENSIONLOOKUPS"):
                    fealookup.use_extension = True
                if prefix or suffix or chain or ignore:
                    if not ignore and targetlookup is None:
                        targetname = self._lookupName(lookup.name + " target")
                        targetlookup = ast.LookupBlock(targetname)
                        self._lookups[targetname] = targetlookup
                        self._gposLookup(lookup, targetlookup)
                    self._gposContextLookup(lookup, prefix, suffix, ignore,
                                            fealookup, targetlookup)
                else:
                    self._gposLookup(lookup, fealookup)

        self._lookups[lookup.name.lower()] = fealookup


def main(args=None):
    import argparse

    parser = argparse.ArgumentParser(
        description="convert VOLT/VTP to feature files.")
    parser.add_argument("font", metavar="FONT",
                        help="input font/VTP file to process")
    parser.add_argument("featurefile", metavar="FEATUEFILE",
                        help="output feature file")
    parser.add_argument("-q", "--quiet", action='store_true',
                        help="Suppress non-error messages")
    parser.add_argument("--traceback", action='store_true',
                        help="Don’t catch exceptions")

    options = parser.parse_args(args)

    if options.quiet:
        log.setLevel(logging.ERROR)
    logging.basicConfig(format="%(levelname)s: %(message)s")

    converter = VoltToFea(options.font)
    try:
        converter.convert(options.featurefile)
    except NotImplementedError as e:
        if options.traceback:
            raise
        location = getattr(e.args[0], "location", None)
        message = '"%s" is not supported' % e
        if location:
            path, line, column = location
            log.error('%s:%d:%d: %s', path, line, column, message)
        else:
            log.error(message)
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
