import re
import sys

from tempfile import NamedTemporaryFile

from fontTools.ttLib import TTFont
from fontTools.feaLib import ast as FeaAst
from fontTools.feaLib.lexer import Lexer as FeaLexer
from fontTools.voltLib import ast
from fontTools.voltLib.parser import Parser

class FeaWriter:
    def __init__(self, font):
        self._font = font
        self._glyph_map = {}
        self._glyph_order = None
        if font is not None:
            self._glyph_order = font.getGlyphOrder()

        self._doc = FeaAst.FeatureFile()
        self._glyph_classes = {}
        self._groups = {}
        self._features = {}
        self._lookups = {}

    @staticmethod
    def _name(name):
        # FIXME: this is using "private" FeaLexer constants.
        if name[0] not in FeaLexer.CHAR_NAME_START_:
            name = "_" + name
        return "".join(c for c in name if c in FeaLexer.CHAR_NAME_CONTINUATION_ or "_")

    @staticmethod
    def _className(name):
        return re.sub(r'[^A-Za-z_0-9.]', "_", name)

    def write(self, path):
        statements = self._doc.statements

        for ftag, scripts in self._features.items():
            feature = FeaAst.FeatureBlock(ftag)
            for stag, langs in scripts.items():
                script = FeaAst.ScriptStatement(stag)
                feature.statements.append(script)
                for ltag, lookups in langs.items():
                    lang = FeaAst.LanguageStatement(ltag)
                    feature.statements.append(lang)
                    for name in lookups:
                        lookup = self._lookups[name]
                        lookupref = FeaAst.LookupReferenceStatement(lookup)
                        feature.statements.append(lookupref)
            statements.append(feature)

        gdef = FeaAst.TableBlock("GDEF")
        gdef.statements.append(
            FeaAst.GlyphClassDefStatement(
                self._glyph_classes.get("BASE", None),
                self._glyph_classes.get("MARK", None),
                self._glyph_classes.get("LIGATURE", None),
                self._glyph_classes.get("COMPONENT", None)))

        statements.append(gdef)

        with open(path, "w") as feafile:
            feafile.write(self._doc.asFea())

    def GroupDefinition(self, group):
        name = self._className(group.name)
        glyphs = FeaAst.GlyphClass(group.glyphSet())
        glyphclass = FeaAst.GlyphClassDefinition(name, glyphs)
        self._groups[group.name] = glyphclass
        self._doc.statements.append(glyphclass)

    def GlyphDefinition(self, glyph):
        try:
            self._glyph_map[glyph.name] = self._glyph_order[glyph.id]
        except TypeError:
            self._glyph_map[glyph.name] = glyph.name

        if glyph.type not in self._glyph_classes:
            self._glyph_classes[glyph.type] = FeaAst.GlyphClass()
        self._glyph_classes[glyph.type].glyphs.append(glyph.name)

    def ScriptDefinition(self, script):
        for lang in script.langs:
            for feature in lang.features:
                if feature.tag not in self._features:
                    self._features[feature.tag] = {}
                if script.tag not in self._features[feature.tag]:
                    self._features[feature.tag][script.tag] = {}
                assert lang.tag not in self._features[feature.tag][script.tag]
                self._features[feature.tag][script.tag][lang.tag] = feature.lookups

    def LookupDefinition(self, lookup):
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
            name = lookup.process_marks
            mark_attachement = FeaAst.GlyphClassName(self._groups[name])
        elif lookup.mark_glyph_set is not None:
            name = lookup.mark_glyph_set
            mark_filtering = FeaAst.GlyphClassName(self._groups[name])

        fea_lookup = FeaAst.LookupBlock(lookup.name)
        if flags or mark_attachement is not None or mark_filtering is not None:
            lookupflags = FeaAst.LookupFlagStatement(flags, mark_attachement,
                                                     mark_filtering)
            fea_lookup.statements.append(lookupflags)

        if lookup.sub is not None:
            prefix = []
            suffix = []
            if lookup.context:
                context = lookup.context[0]
                if context.left:
                    left = context.left[0] # FIXME
                    prefix = [FeaAst.GlyphClass([FeaAst.GlyphName(g) for g in left.glyphSet()])]
                if context.right:
                    right = context.right[0] # FIXME
                    suffix = [FeaAst.GlyphClass([FeaAst.GlyphName(g) for g in right.glyphSet()])]

            if isinstance(lookup.sub, ast.SubstitutionLigatureDefinition):
                for key, val in lookup.sub.mapping.items():
                    # FIXME
                    glyphs = [FeaAst.GlyphName(g) for g in key.glyphSet()]
                    replacement = FeaAst.GlyphName(val.glyphSet()[0])
                    subst = FeaAst.LigatureSubstStatement(prefix, glyphs,
                                suffix, replacement, False)
                    fea_lookup.statements.append(subst)

        if lookup.pos is not None:
            pass

        self._lookups[lookup.name] = fea_lookup
        if lookup.comments is not None:
            self._doc.statements.append(FeaAst.Comment(lookup.comments))
        self._doc.statements.append(fea_lookup)

def main(filename, outfilename):
    font = None
    try:
        font = TTFont(filename)
        if "TSIV" in font:
            with NamedTemporaryFile(delete=False) as temp:
                temp.write(font["TSIV"].data)
                temp.flush()
                parser = Parser(temp.name)
    except:
        parser = Parser(filename)
    writer = FeaWriter(font)
    res = parser.parse()
    reported = []

    for s in res.statements:
        name = type(s).__name__
        if hasattr(writer, name):
            getattr(writer, name)(s)
        elif not name in reported:
            print("Can’t handle: %s" % name)
            reported.append(name)

    writer.write(outfilename)

if __name__ == '__main__':
    if len(sys.argv) == 3:
        main(sys.argv[1], sys.argv[2])
    else:
        print('Usage: %s voltfile feafile' % sys.argv[0])
        sys.exit(1)
