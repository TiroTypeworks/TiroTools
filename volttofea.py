import re
import sys

from tempfile import NamedTemporaryFile

from fontTools.ttLib import TTFont
from fontTools.feaLib.lexer import Lexer as FeaLexer
from fontTools.voltLib.ast import LookupDefinition
from fontTools.voltLib.parser import Parser

class FeaWriter():
    def __init__(self):
        self._classes = []
        self._lookups = []
        self._features = []

    @staticmethod
    def _name(name):
        # FIXME: this is using "private" FeaLexer constants.
        if name[0] not in FeaLexer.CHAR_NAME_START_:
            name = "_" + name
        return "".join(c for c in name if c in FeaLexer.CHAR_NAME_CONTINUATION_ or "_")

    @staticmethod
    def _className(name):
        return "@" + re.sub(r'[^A-Za-z_0-9.]', "_", name)

    def write(self, path):
        items = []
        if self._classes:
            items.append("\n".join(self._classes))
        if self._lookups:
            items.append("\n\n".join(self._lookups))
        if self._features:
            items.append("\n\n".join(self._features))
        fea = "\n".join(items)

        with open(path, "w") as feafile:
            feafile.write(fea)
            feafile.write("\n")

    def WriteGroupDefinition(self, group):
        name = self._className(group.name)
        glyphs = group.glyphSet()
        self._classes.append("%s = [%s];" % (name, " ".join(glyphs)))

def main(filename, outfilename):
    try:
        font = TTFont(filename)
        if "TSIV" in font:
            with NamedTemporaryFile(delete=False) as temp:
                temp.write(font["TSIV"].data)
                temp.flush()
                parser = Parser(temp.name)
    except:
        parser = Parser(filename)
    writer = FeaWriter()
    res = parser.parse()
    reported = []

    for s in res.statements:
        name = type(s).__name__
        methodname = "Write" + name
        if hasattr(writer, methodname):
            getattr(writer, methodname)(s)
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
