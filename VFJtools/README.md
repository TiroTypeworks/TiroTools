VFJ tools
=====

This folder contains tools for manipulating or converting FontLab 7 .vfj sources files. These tools were written for us by Khaled Hosny.

Dependencies
------------

These tools require Python 3 and the vfj.py module (note: the latter is not yet a general purpose module, and only implements those things needed for the current scripts).

vfj-propagate-anchors.py
-----

vfj-propagate-anchors.py will propoagate mark attachment anchors in a .vfj file to composite glyphs based on existing mark-to-base and mark-to-mark anchors.

Usage example:

```
python3 vfj-propagate-anchors.py input.vfj output.vfj
```

vfj-to-volt.py
-----

vfj-to-volt.py will write MS VOLT format sources from a .vfj file. Currently, this only supports mark and mkmk feature anchor attachment lookups and associated groups. Output is .vtl lookup and .vtg. group file for import into VOLT projects.

vfj-to-volt.py uses glyph category entries in the .vfj source to identify marks, and hence to distinguish anchors to use in the discrete mark or mkmk lookups.

If a .vfj contains multiple masters, vfj-to-volt.py will write lookups and groups for each master.


Usage example:

```
python3 vfj-to-volt.py input.vfj --anchors
```