VTP tools
=====

This folder contains tools for manipulating MS VOLT .vtp source files. These tools were written for us by Khaled Hosny.

Dependencies
------------

These tools require Python 3 and FontTools

vtp-scale.py
-----

vtp-scale.py will scale all GPOS data in a .vtp source file. This is useful if scaling outlines, metrics, etc. to a new UPM value. Note that GPOS data will be rounded to the nearest integer.

Usage example: to double the scale of GPOS data:

```
python3 vtp-scale.py input.vtp output.vtp -f 2
```
The tool can also be used on a font files containing a TSIV source table:

```
python3 vtp-scale.py input.ttf output.ttf -f 2
```

vtp-skew.py
-----

vtp-skew.py will recalculate all GPOS data in a .vtp source file based on a slant angle, applying rise-over-run adjustments to the horizontal position of non-zero vertical positions. This is useful if creating an obliqued version of a font.

Usage example: to slant the GPOS data 12° to the right:

```
python3 vtp-skew.py input.vtp output.vtp -a 12
```

To slant to the left, use a negative value.

The tool can also be used on a font files containing a TSIV source table:

```
python3 vtp-skew.py input.ttf output.ttf -a 12
```

vtp-gdef.py
----

The vtp-gdef.py tool is used to set GDEF glyph classes in a .vtp file from an input text file. The text file has the follwing format:

```
# class1
glyphname1
glyphname2
# class2
glyphname3
```

Where glyph class is one of “base”, “mark”, “ligature”, and “component”. For ligatures, glyph name can optionally be followed by space then the number of components, e.g. `ffi 3`.

Usage example:

```
python3 vtp-gdef.py input.vtp gdef.txt output.vtp
```

Any missing glyphs from the GDEF text file will be given “base” glyph class, and this can be overriden using `--missing` option. To set missing glyphs to mark:

```
python3 vtp-gdef.py input.vtp gdef.txt output.vtp --missing=mark
```

To keep missing glyphs unchaged:
```
python3 vtp-gdef.py input.vtp gdef.txt output.vtp --missing=keep
```