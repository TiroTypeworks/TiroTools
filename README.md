Volto
=====

MS VOLT `.vtp` to AFDKO `.fea` OpenType Layout converter.

Installation
------------

Volto requires Python 3 and FontTools, to install from the GIT repository:
```
pip install git+https://github.com/TiroTypeworks/Volto
```

Usage
-----

To convert a VTP project file:
```
volto input.vtp output.fea
```

It is also possible convert font files with `TSIV` table (as saved from Volt),
in this case the glyph names used in the Volt project will be mapped to the
actual glyph names in the font files when written to the feature file:
```
volto input.ttf output.fea
```

The `--quiet` option can be used to suppress warnings.

The `--traceback` can be used to get Python traceback in case of exceptions,
instead of suppressing the traceback.


Limitations
-----------

* Not all VOLT features are supported, the script will error if it it
  encounters something it does not understand. Please report an issue if this
  happens.
* AFDKO feature file syntax for mark positioning is awkward and does not allow
  setting the mark coverage. It also defines mark anchors globally, as a result
  some mark positioning lookups might cover many marks than what was in the VOLT
  file. This should not be an issue in practice, but if it is then the only way
  is to modify the VOLT file or the generated feature file manually to use unique
  mark anchors for each lookup.
* VOLT allows subtable breaks in any lookup type, but AFDKO feature file
  implementations vary in their support; currently AFDKO’s makeOTF supports
  subtable breaks in pair positioning lookups only, while FontTools’ feaLib
  support it for most substitution lookups and only some positioning lookups.
