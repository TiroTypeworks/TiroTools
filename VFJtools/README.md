VFJ tools
=====

This folder contains tools for manipulating or converting FontLab 7 .vfj sources files. These tools were written for us by Khaled Hosny.

Dependencies
------------

These tools require Python 3 and the vfj.py module (note: the latter is not yet a general purpose module, and only implements those things needed for the current scripts).

vfj-redefine-anchors
-----

vfj-redefine-anchors.py uses a CSV input file to update the x,y position of a mark anchor on a key mark glyph in a VFJ file and then calculates and applies offsets to move all other instances of the mark anchor and corresponding base anchors. The purpose is to enable redefinition of anchor positions while retaining the relative positions of marks and bases.

Usage example:

```
python3 vfj-redefine-anchors.py -p position.csv input.vfj output.vfj
```

The format of the CSV file is one anchor per line as so:

```
anchorname,keyglyphname,xposition,yposition
```

e.g.

```
_top,dieresiscomb,-200,450
```

Note: the x,y position should be the new anchor location, not the delta from the current location (which will be calculated by the script and applied to matching and corresponding anchors), and the CSV should only redefine each anchor once, on a single key glyph. The key glyph can be any mark glyph that has the named anchor.

vfj-propagate-anchors.py
-----

vfj-propagate-anchors.py will propagate mark attachment anchors in a .vfj file to composite glyphs based on existing mark-to-base and mark-to-mark anchors.

Usage example:

```
python3 vfj-propagate-anchors.py input.vfj output.vfj
```

vfj-to-volt.py
-----

vfj-to-volt.py will write MS VOLT format sources from a .vfj file. Currently, this only supports mark and mkmk feature anchor attachment, and kern feature lookups and associated groups. Output is .vtl lookup and .vtg group files for import into VOLT projects.

vfj-to-volt.py uses glyph category entries in the .vfj source to identify marks, and hence to distinguish anchors to use in the discrete mark or mkmk lookups.

When writing kerning lookups, vfj-to-volt.py will write \PP1 and \PP2 lookups for exception and class kerning, respectively.

If a .vfj contains multiple masters, vfj-to-volt.py will write lookups and groups for each master.


Usage example, to produce anchor files:

```
python3 vfj-to-volt.py input.vfj --anchors
```

To produce kerning files:

```
python3 vfj-to-volt.py input.vfj --kerning
```

To do both at the same time:

```
python3 vfj-to-volt.py input.vfj --anchors --kerning
```