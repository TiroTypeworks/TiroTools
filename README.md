TiroTools
=====

Assorted font production scripts, mostly involving either conversion of data between font development source formats, or manipulation of source formats.

Please see individual folder readme files for installation, usage, or dependency notes.

All scripts in this repo are licensed under the MIT open source license.

Current tool list
------------

### Volto
Converts MS Visual OpenType Layout Tool (VOLT) projects to AFDKO feature file syntax.

### VTPtools : vtp-scale
Scales all GPOS data in a VOLT project file.

### VTPtools : vtp-skew
Adjusts rise-over-run coordinates for GPOS data in a VOLT project file to a defined slant angle.

### VFJtools : vfj-propagate-anchors
Propagates anchors from base to composite glyphs in FontLab 7 .vfj sources.

### VFJtools : vfj-to-volt
Exports VOLT .vtl lookups and .vtg group sources from FontLab 7 .vfj sources.