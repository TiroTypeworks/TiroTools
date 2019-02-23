Volto
=====

A VOLT/VTP to feature files converter.

Limitations
-----------

* Not all VOLT features are supported, the script will assert if it it
  encounters something it does not understand. Please report an issue if this
  happens.
* Feature files syntax for mark positioning is awkward and does not allow
  setting the mark coverage. It also defines mark anchors globally, as a result
  some mark positioning lookups might cover many marks than what was in the VOLT
  file. This should not be an issue in practice, but if it is then the only way
  is to modify the VOLT file or the generated feature file manually to use unique
  mark anchors for each lookup.
* Subtables (in VOLT named as “base\sub”) in feature files only supported for
  pair positioning lookups, so using subtables for other kinds of lookups will
  result in writing each as a separate lookup, which might change the behaviour
  of the built font file.
