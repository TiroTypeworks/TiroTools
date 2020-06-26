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

vtp-skew.py will recalculate all GPOS data in a .vtp source file based on a slant angle, applying rise-over-run adjustments to the horizontal position of non-zero vertical positions. This is useful if creating an obliqued version of a font. *NB: assumes that default y coordinate of anchors is zero, so may not produce desired results if anchors are otherwise defined.*

Usage example: to slant the GPOS data 12° to the right:

```
vtp-skew input.vtp output.vtp -a 12
```

To slant to the left, use a negative value.

The tool can also be used on a font files containing a TSIV source table:

```
vtp-skew input.ttf output.ttf -a 12
```