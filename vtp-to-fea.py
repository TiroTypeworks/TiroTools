import re

from collections import OrderedDict
from tempfile import NamedTemporaryFile

from fontTools.ttLib import TTFont
from fontTools.feaLib import ast
from fontTools.voltLib import ast as VoltAst
from fontTools.voltLib.parser import Parser as VoltParser


class VtpToFea:
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
        self._ligatures = set()

        self._markclasses = OrderedDict()
        self._anchors = {}

        self._settings = {}

    def _lookupName(self, name, suffix=""):
        # FIXME: make sure sanitized name is unique.
        name = name + suffix
        return self._NOT_LOOKUP_NAME_RE.sub("_", name)

    def _className(self, name):
        # FIXME: make sure sanitized name is unique.
        return self._NOT_CLASS_NAME_RE.sub("_", name)

    def _parse(self, filename):
        font = None
        try:
            font = TTFont(filename)
            if "TSIV" in font:
                with NamedTemporaryFile(delete=False) as temp:
                    temp.write(font["TSIV"].data)
                    temp.flush()
                    parser = VoltParser(temp.name)
        except:
            parser = VoltParser(filename)

        return parser.parse(), font

    def convert(self, path):
        volt_doc, font = self._parse(self._filename)

        if font is not None:
            self._glyph_order = font.getGlyphOrder()

        fea = ast.FeatureFile()
        statements = fea.statements

        for statement in volt_doc.statements:
            if isinstance(statement, VoltAst.GlyphDefinition):
                self._glyphDefinition(statement)
            elif isinstance(statement, VoltAst.AnchorDefinition):
                self._anchorDefinition(statement)
            elif isinstance(statement, VoltAst.SettingDefinition):
                self._settingDefinition(statement)
            elif isinstance(statement, VoltAst.GroupDefinition):
                self._groupDefinition(statement)
            elif isinstance(statement, VoltAst.ScriptDefinition):
                self._scriptDefinition(statement)
            elif not isinstance(statement, VoltAst.LookupDefinition):
                assert False, "%s is not handled" % statement

        # Lookup difinitions need to be handled last as they reference glyph
        # and mark classes that might be defined after them.
        for statement in volt_doc.statements:
            if isinstance(statement, VoltAst.LookupDefinition):
                self._lookupDefinition(statement)

        statements.extend(self._markclasses.values())
        statements.extend(self._glyphclasses.values())
        statements.extend(self._lookups.values())

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
            if isinstance(item, VoltAst.GlyphName):
                items.append(self._glyphName(item))
            elif isinstance(item, VoltAst.GroupName):
                items.append(self._groupName(item))
            elif isinstance(item, VoltAst.Enum):
                items.append(self._enum(item))
            else:
                assert False, "%s is not handled" % item
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
            self._ligatures.add(glyph.name)

    def _scriptDefinition(self, script):
        for lang in script.langs:
            for feature in lang.features:
                if feature.tag not in self._features:
                    self._features[feature.tag] = OrderedDict()
                if script.tag not in self._features[feature.tag]:
                    self._features[feature.tag][script.tag] = OrderedDict()
                assert lang.tag not in self._features[feature.tag][script.tag]
                self._features[feature.tag][script.tag][lang.tag] = feature.lookups

    def _settingDefinition(self, setting):
        if setting.name.startswith("COMPILER_"):
            self._settings[setting.name] = setting.value

    def _adjustment(self, adjustment):
        adv, dx, dy, adv_adjust_by, dx_adjust_by, dy_adjust_by = adjustment
        # FIXME
        assert not adv_adjust_by
        assert not dx_adjust_by
        assert not dy_adjust_by
        return ast.ValueRecord(xPlacement=dx, yPlacement=dy, xAdvance=adv,
                               xPlaDevice=None, yPlaDevice=None,
                               xAdvDevice=None)

    def _anchor(self, adjustment):
        adv, dx, dy, adv_adjust_by, dx_adjust_by, dy_adjust_by = adjustment
        # FIXME
        assert not adv_adjust_by
        assert not dx_adjust_by
        assert not dy_adjust_by
        return ast.Anchor(dx or 0, dy or 0)

    def _anchorDefinition(self, anchordef):
        glyphname = anchordef.glyph_name
        anchor = self._anchor(anchordef.pos)

        if anchordef.name.startswith("MARK_"):
            name = "_".join(anchordef.name.split("_")[1:])
            markclass = ast.MarkClass(self._className(name))
            glyph = self._glyphName(glyphname)
            markdef = ast.MarkClassDefinition(markclass, anchor, glyph)
            self._markclasses[(glyphname, anchordef.name)] = markdef
        else:
            if glyphname not in self._anchors:
                self._anchors[glyphname] = {}
            self._anchors[glyphname][anchordef.name] = anchor

    def _gposLookup(self, lookup, fealookup):
        statements = fealookup.statements

        pos = lookup.pos
        if isinstance(pos, VoltAst.PositionAdjustPairDefinition):
            for (idx1, idx2), (pos1, pos2) in pos.adjust_pair.items():
                coverage_1 = pos.coverages_1[idx1 - 1]
                coverage_2 = pos.coverages_2[idx2 - 1]

                # If not both are groups, use “enum pos” otherwise makeotf will
                # fail.
                enumerated = False
                for item in coverage_1 + coverage_2:
                    if not isinstance(item, VoltAst.GroupName):
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
        elif isinstance(pos, VoltAst.PositionAdjustSingleDefinition):
            for a, b in pos.adjust_single:
                glyphs = self._coverage(a)
                record = self._adjustment(b)
                assert len(glyphs) == 1
                statements.append(ast.SinglePosStatement(
                    [(glyphs[0], record)], [], [], False))
        elif isinstance(pos, VoltAst.PositionAttachDefinition):
            anchors = {}
            for _, mark in pos.coverage_to:
                markclass = ast.MarkClass(self._className(mark))
                for base in pos.coverage:
                    for name in base.glyphSet():
                        if name not in anchors:
                            anchors[name] = []
                        if mark not in anchors[name]:
                            anchors[name].append(mark)

            for name in anchors:
                marks = []
                for mark in anchors[name]:
                    markclass = ast.MarkClass(self._className(mark))
                    anchor = self._anchors[name][mark]
                    marks.append((anchor, markclass))

                base = self._glyphName(name)
                if name in self._marks:
                    mark = ast.MarkMarkPosStatement(base, marks)
                elif name in self._ligatures:
                    # FIXME
                    assert False
                    #mark = ast.MarkLigPosStatement(base, ())
                else:
                    mark = ast.MarkBasePosStatement(base, marks)
                statements.append(mark)
        else:
            assert False, "%s is not handled" % pos

    def _gposContextLookup(self, lookup, prefix, suffix, ignore, fealookup,
                           targetlookup):
        statements = fealookup.statements

        # FIXME
        assert not ignore

        pos = lookup.pos
        if isinstance(pos, VoltAst.PositionAdjustPairDefinition):
            for (idx1, idx2), (pos1, pos2) in pos.adjust_pair.items():
                glyphs1 = self._coverage(pos.coverages_1[idx1 - 1])
                glyphs2 = self._coverage(pos.coverages_2[idx2 - 1])
                record1 = self._adjustment(pos1)
                record2 = self._adjustment(pos2)
                assert len(glyphs1) == 1
                assert len(glyphs2) == 1
                glyphs = (glyphs1[0], glyphs2[0])
                lookups = (targetlookup, targetlookup)
                statements.append(ast.ChainContextPosStatement(
                    prefix, glyphs, suffix, lookups))
        elif isinstance(pos, VoltAst.PositionAdjustSingleDefinition):
            lookups = [targetlookup]
            glyphs = [ast.GlyphClass()]
            for a, b in pos.adjust_single:
                glyph = self._coverage(a)
                record = self._adjustment(b)
                glyphs[0].extend(glyph)
            statements.append(ast.ChainContextPosStatement(
                prefix, glyphs, suffix, lookups))
        elif isinstance(pos, VoltAst.PositionAttachDefinition):
            lookups = [targetlookup]
            glyphs = [ast.GlyphClass()]
            for coverage, _ in pos.coverage_to:
                glyphs[0].extend(self._coverage(coverage))
            statements.append(ast.ChainContextPosStatement(
                prefix, glyphs, suffix, lookups))
        else:
            assert False, "%s is not handled" % pos

    def _gsubLookup(self, lookup, prefix, suffix, ignore, fealookup):
        statements = fealookup.statements

        sub = lookup.sub
        for key, val in sub.mapping.items():
            subst = None
            glyphs = self._coverage(key)
            replacement = self._coverage(val)
            if ignore:
                chain_context = (prefix, glyphs, suffix)
                subst = ast.IgnoreSubstStatement([chain_context])
            elif isinstance(sub, VoltAst.SubstitutionSingleDefinition):
                assert(len(glyphs) == 1)
                assert(len(replacement) == 1)
                subst = ast.SingleSubstStatement(glyphs, replacement,
                            prefix, suffix, False)
            elif isinstance(sub, VoltAst.SubstitutionMultipleDefinition):
                assert(len(glyphs) == 1)
                subst = ast.MultipleSubstStatement(prefix, glyphs[0], suffix,
                            replacement)
            elif isinstance(sub, VoltAst.SubstitutionLigatureDefinition):
                assert(len(replacement) == 1)
                subst = ast.LigatureSubstStatement(prefix, glyphs,
                            suffix, replacement[0], False)
            else:
                assert False, "%s is not handled" % sub
            statements.append(subst)

    def _lookupDefinition(self, lookup):
        mark_attachement = None
        mark_filtering = None

        flags = 0
        if lookup.direction == "RTL":
            flags |= 1
        if not lookup.process_base:
            flags |= 2
        # FIXME: Does VOLT support this?
        #if not lookup.process_ligatures:
        #    flags |= 4
        if not lookup.process_marks:
            flags |= 8
        elif isinstance(lookup.process_marks, str):
            mark_attachement = self._groupName(lookup.process_marks)
        elif lookup.mark_glyph_set is not None:
            mark_filtering = self._groupName(lookup.mark_glyph_set)

        fealookup = ast.LookupBlock(self._lookupName(lookup.name))

        if lookup.comments is not None:
            fealookup.statements.append(ast.Comment(lookup.comments))

        if flags or mark_attachement is not None or mark_filtering is not None:
            lookupflags = ast.LookupFlagStatement(flags, mark_attachement,
                                                  mark_filtering)
            fealookup.statements.append(lookupflags)

        # FIXME
        assert not lookup.reversal

        contexts = []
        if lookup.context:
            for context in lookup.context:
                prefix = self._context(context.left)
                suffix = self._context(context.right)
                ignore = context.ex_or_in == "EXCEPT_CONTEXT"
                contexts.append([prefix, suffix, ignore])
        else:
            contexts.append([[], [], False])

        targetlookup = None
        for prefix, suffix, ignore in contexts:
            if lookup.sub is not None:
                self._gsubLookup(lookup, prefix, suffix, ignore, fealookup)

            if lookup.pos is not None:
                if self._settings.get("COMPILER_USEEXTENSIONLOOKUPS"):
                    fealookup.use_extension = True
                if prefix or suffix or ignore:
                    if not ignore and targetlookup is None:
                        targetname = self._lookupName(lookup.name, " target")
                        targetlookup = ast.LookupBlock(targetname)
                        self._lookups[targetname] = targetlookup
                        self._gposLookup(lookup, targetlookup)
                    self._gposContextLookup(lookup, prefix, suffix, ignore,
                                            fealookup, targetlookup)
                else:
                    self._gposLookup(lookup, fealookup)

        self._lookups[lookup.name.lower()] = fealookup


def main(filename, outfilename):
    converter = VtpToFea(filename)
    converter.convert(outfilename)

if __name__ == '__main__':
    import sys
    if len(sys.argv) == 3:
        main(sys.argv[1], sys.argv[2])
    else:
        print('Usage: %s voltfile feafile' % sys.argv[0])
        sys.exit(1)
