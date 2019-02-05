import re

from collections import OrderedDict
from tempfile import NamedTemporaryFile

from fontTools.ttLib import TTFont
from fontTools.feaLib import ast
from fontTools.voltLib import ast as VoltAst
from fontTools.voltLib.parser import Parser as VoltParser


class VtpToFea:
    _LOOKUP_NAME_START_RE = re.compile(r"[A-Za-z_*:.\^~!\\]")
    _NOT_LOOKUP_NAME_RE = re.compile(r"[^A-Za-z0-9_.*:\^~!/]")
    _NOT_CLASS_NAME_RE = re.compile(r"[^A-Za-z_0-9.]")

    def __init__(self, filename):
        self._filename = filename

        self._glyph_map = {}
        self._glyph_order = None

        self._gdef = {}
        self._groups = {}
        self._features = OrderedDict()
        self._lookups = {}

        self._marks = set()
        self._ligatures = set()

        self._mark_classes = {}
        self._anchors = {}

    def _lookupName(self, name):
        if self._LOOKUP_NAME_START_RE.match(name[0]) is None:
            name = "_" + name
        out = self._NOT_LOOKUP_NAME_RE.sub("_", name)
        return out

    def _className(self, name):
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

        for statement in volt_doc.statements:
            if isinstance(statement, VoltAst.GlyphDefinition):
                self._glyphDefinition(statement)
            elif isinstance(statement, VoltAst.AnchorDefinition):
                self._anchorDefinition(statement)

        for statement in volt_doc.statements:
            ret = None
            if isinstance(statement, VoltAst.GlyphDefinition):
                # Handled above
                pass
            elif isinstance(statement, VoltAst.AnchorDefinition):
                # Handled above
                pass
            elif isinstance(statement, VoltAst.SettingDefinition):
                # Nothing here can be written to feature files.
                pass
            elif isinstance(statement, VoltAst.ScriptDefinition):
                ret = self._scriptDefinition(statement)
            elif isinstance(statement, VoltAst.GroupDefinition):
                ret = self._groupDefinition(statement)
            elif isinstance(statement, VoltAst.LookupDefinition):
                ret = self._lookupDefinition(statement)
            else:
                assert False, "%s is not handled" % statement
            fea.statements.extend(ret if ret else [])

        for ftag, scripts in self._features.items():
            feature = ast.FeatureBlock(ftag)
            for stag, langs in scripts.items():
                script = ast.ScriptStatement(stag)
                feature.statements.append(script)
                for ltag, lookups in langs.items():
                    lang = ast.LanguageStatement(ltag)
                    feature.statements.append(lang)
                    for name in lookups:
                        lookup = self._lookups[name.lower()]
                        lookupref = ast.LookupReferenceStatement(lookup)
                        feature.statements.append(lookupref)
            fea.statements.append(feature)

        if self._gdef:
            gdef = ast.TableBlock("GDEF")
            gdef.statements.append(
                ast.GlyphClassDefStatement(self._gdef.get("BASE"),
                                           self._gdef.get("MARK"),
                                           self._gdef.get("LIGATURE"),
                                           self._gdef.get("COMPONENT")))

            fea.statements.append(gdef)

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
        return ast.GlyphClassName(self._groups[name.lower()])

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

        self._groups[group.name.lower()] = glyphclass
        return [glyphclass]

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
        glyphs = ast.GlyphClass([self._glyphName(glyphname)])

        name = anchordef.name
        if name.startswith("MARK_"):
            name = "_".join(anchordef.name.split("_")[1:])

        if name not in self._mark_classes:
            self._mark_classes[name] = ast.MarkClass(self._className(name))
        markclass = self._mark_classes[name]

        mark = None
        if anchordef.name.startswith("MARK_"):
            mark = ast.MarkClassDefinition(markclass, anchor, glyphs)
        else:
            if glyphname in self._marks:
                mark = ast.MarkMarkPosStatement(glyphs, [(anchor, markclass)])
            elif glyphname in self._ligatures:
                # FIXME
                assert False
                #mark = ast.MarkLigPosStatement(glyphs, ())
            else:
                mark = ast.MarkBasePosStatement(glyphs, [(anchor, markclass)])

        if glyphname not in self._anchors:
            self._anchors[glyphname] = {}
        self._anchors[glyphname][anchordef.name] = mark

    def _gposLookup(self, lookup, fealookup):
        statements = fealookup.statements

        pos = lookup.pos
        if isinstance(pos, VoltAst.PositionAdjustPairDefinition):
            for (idx1, idx2), (pos1, pos2) in pos.adjust_pair.items():
                glyphs1 = self._coverage(pos.coverages_1[idx1 - 1])
                glyphs2 = self._coverage(pos.coverages_2[idx2 - 1])
                record1 = self._adjustment(pos1)
                record2 = self._adjustment(pos2)
                assert len(glyphs1) == 1
                assert len(glyphs2) == 1
                statements.append(ast.PairPosStatement(
                    glyphs1[0], record1, glyphs2[0], record2))
        elif isinstance(pos, VoltAst.PositionAdjustSingleDefinition):
            for a, b in pos.adjust_single:
                glyphs = self._coverage(a)
                record = self._adjustment(b)
                assert len(glyphs) == 1
                statements.append(ast.SinglePosStatement(
                    [(glyphs[0], record)], [], [], False))
        elif isinstance(pos, VoltAst.PositionAttachDefinition):
            for glyphs, mark in pos.coverage_to:
                for glyph in glyphs:
                    for name in glyph.glyphSet():
                        statements.append(self._anchors[name]["MARK_" + mark])
                for base in pos.coverage:
                    for name in base.glyphSet():
                        statements.append(self._anchors[name][mark])
        else:
            assert False, "%s is not handled" % pos

    def _gposContextLookup(self, lookup, prefix, suffix, ignore, fealookup,
                           sublookup):
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
                lookups = (sublookup, sublookup)
                statements.append(ast.ChainContextPosStatement(
                    prefix, glyphs, suffix, lookups))
        elif isinstance(pos, VoltAst.PositionAdjustSingleDefinition):
            lookups = [sublookup]
            glyphs = [ast.GlyphClass()]
            for a, b in pos.adjust_single:
                glyph = self._coverage(a)
                record = self._adjustment(b)
                glyphs[0].extend(glyph)
            statements.append(ast.ChainContextPosStatement(
                prefix, glyphs, suffix, lookups))
        elif isinstance(pos, VoltAst.PositionAttachDefinition):
            lookups = [sublookup]
            glyphs = [ast.GlyphClass(self._coverage(pos.coverage))]
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

        statements = []
        for prefix, suffix, ignore in contexts:
            if lookup.sub is not None:
                self._gsubLookup(lookup, prefix, suffix, ignore, fealookup)

            if lookup.pos is not None:
                if prefix or suffix or ignore:
                    if not ignore:
                        subname = self._lookupName(lookup.name) + "_sub"
                        sublookup = ast.LookupBlock(subname)
                        statements.append(sublookup)
                        self._gposLookup(lookup, sublookup)
                    self._gposContextLookup(lookup, prefix, suffix, ignore,
                                            fealookup, sublookup)
                else:
                    self._gposLookup(lookup, fealookup)

        self._lookups[lookup.name.lower()] = fealookup

        if lookup.comments is not None:
            statements.append(ast.Comment(lookup.comments))
        statements.append(fealookup)

        return statements


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
