TiroTools
=====

Assorted font production scripts, mostly involving either conversion of data between font development source formats, or manipulation of source formats.

All scripts in this repo are licensed under the MIT open source license.

*If you are looking for the* ***Volto*** *tool to convert Microsoft VOLT .vtp to Adobe .fea syntax, this tool has now been integrated into the [FontTools](https://github.com/fonttools/fonttools) project as the* `voltLib.voltToFea` *module.*

Setup
------------

It is recommended to create and activate a virtual environment in which to run the tools. From the top level, TiroTools folder:

```
# Create a new virtualenv
python3 -m venv venv
# Activate env
source venv/bin/activate
# Install dependencies
pip3 install -r requirements.txt
```

For subsequent use (presuming the requirements have not changed), only the second of those steps will be required.


Please see individual folder readme files for installation, usage, or dependency notes.

Current tool list
------------
### Builder : tirobuild
See [Builder/README.md](Builder/README.md)

### TXTtools : sinhala
Processes text in Sinhala script to affect various orthographic forms using Unicode formatting control characters.

### VTPtools : vtp-scale
Scales all GPOS data in a VOLT project file.

### VTPtools : vtp-skew
Adjusts rise-over-run coordinates for GPOS data in a VOLT project file to a defined slant angle.

### VTPtools : vtp-gdef
Sets the GDEF glyph classes in a VOLT project from an input text file.

### VFJtools : vfj-propagate-anchors
Propagates anchors from base to composite glyphs in FontLab 7 .vfj sources.

### VFJtools : vfj-redefine-anchors
Redefines anchor locations while retaining relative position of anchored marks to bases, ligatures, and other marks.

### VFJtools : vfj-to-volt
Exports VOLT .vtl lookups and .vtg group sources from FontLab 7 .vfj sources.






