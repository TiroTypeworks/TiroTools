import sys

from fontTools.voltLib.parser import Parser
from fontTools.voltLib.ast import LookupDefinition

class FeaWriter():
    def __init__(self):
        self._classes = []
        self._lookups = []
        self._features = []

    def _sanitizeName(self, name, prefix=""):
        name = name.replace(" ", "_")
        if prefix:
            name = prefix + "_" + name
        return name

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
        name = self._sanitizeName(group.name, "@c")
        glyphs = group.glyphSet()
        self._classes.append("%s = [%s];" % (name, " ".join(glyphs)))

def main(filename, outfilename):
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
