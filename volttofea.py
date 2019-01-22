import re
import sys

from tempfile import NamedTemporaryFile

from fontTools.ttLib import TTFont
from fontTools.feaLib import ast as FeaAst
from fontTools.feaLib.lexer import Lexer as FeaLexer
from fontTools.voltLib.ast import LookupDefinition
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
        gdef = FeaAst.TableBlock("GDEF")
        gdef.statements.append(
            FeaAst.GlyphClassDefStatement(
                self._glyph_classes.get("BASE", None),
                self._glyph_classes.get("MARK", None),
                self._glyph_classes.get("LIGATURE", None),
                self._glyph_classes.get("COMPONENT", None)))

        self._doc.statements.append(gdef)

        with open(path, "w") as feafile:
            feafile.write(self._doc.asFea())

    def GroupDefinition(self, group):
        name = self._className(group.name)
        glyphs = FeaAst.GlyphClass(group.glyphSet())
        self._doc.statements.append(FeaAst.GlyphClassDefinition(name, glyphs))

    def GlyphDefinition(self, glyph):
        try:
            self._glyph_map[glyph.name] = self._glyph_order[glyph.id]
        except TypeError:
            self._glyph_map[glyph.name] = glyph.name

        if glyph.type not in self._glyph_classes:
            self._glyph_classes[glyph.type] = FeaAst.GlyphClass()
        self._glyph_classes[glyph.type].glyphs.append(glyph.name)

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
