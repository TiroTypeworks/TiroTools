Volto additional tools
=====

This folder contains additional tools for manipulating MS VOLT .vtp source files. The tools were written for us by Khaled Hosny, and are provided as-is under the same MIT license as the main Volto tool.

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

vtp-skew.py
-----

vtp-skew.py will recalculate all GPOS data in a .vtp source file based on a slant angle, applying rise-over-run adjustments to the horizontal position of non-zero vertical positions. This is useful if creating an obliqued version of a font.

Usage example: to slant the GPOS data 12° to the right:

```
vtp-skew input.vtp output.vtp -a 12
```

To slant to the left, use a negative value.