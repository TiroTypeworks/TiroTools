TXT tools
=====

This folder contains tools for manipulating text files, e.g. inserting Unicode formatting control characters to affect different orthographic preferences.

Dependencies
------------

These tools require Python 3.

sinhala.py
-----

This Sinhala text formatting tool will contextually insert (or delete) the Zero Width Joiner (ZWJ, U+200D) control character to affect four different orthographic forms of Sinhala script. The orthographic forms are cumulative, so the -l option includes the -y insertions, and the -c option includes the -y and -l insertions.

Usage:

```
python3 sinhala.py [-h] [-r] [-y | -l | -c] input output
```

The options are:

**-h** displays the script help text

**-r** resets* text to use explicit *al-lakuna* (virama) throughout by removing all ZWJ characters**.

**-y** inserts ZWJ after select *al-lakuna* characters to trigger formatting of *rephaya, rakaaraansaya* and *yansaya* forms.

**-l** inserts ZWJ after select *al-lakuna* characters to trigger traditional ligature forms*** as well as *rephaya, rakaaraansaya* and *yansaya* forms.

**-c** inserts ZWJ before all remaining *al-lakuna* characters to trigger touching behaviour for all remaining conjuncts, as well as traditional ligature and *rephaya, rakaaraansaya* and *yansaya* forms.
_____

*The -r option can be used with any of the other three options, so that you can e.g. remove all formatting from existing text then insert ZWJ as needed in one pass. The other options are mutually exclusive.

**The -r option also removes any Zero Width Non-Joiner (ZWNJ, U+200C) characters, although these are not expected in Sinhala text, having no defined formatting role for the script in the Unicode Standard.

***These ligature forms are font-specific. The ligatures specified in the script conform to those supported in the Tiro Sinhala font, consisting of ක්‍ව ක්‍ෂ ග්‍ධ ච්‍ච ඤ්‍ච ඤ්‍ඡ ට්‍ඨ ත්‍ථ ව ද්‍ධ ද්‍ව න්‍ථ න්‍ද න්‍ධ න්‍ව ඳ්‍ඨ ඳ්‍ධ ඳ්‍ව බ්‍බ