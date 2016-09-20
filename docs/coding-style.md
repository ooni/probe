# Hacking on OONI

This documents gives guidelines on where to start looking
for helping out in developing OONI and what guidelines you
should follow when writing code.

We try to follow the general python best practices and styling
guides as specified in PEP.

    Beautiful is better than ugly.
    Explicit is better than implicit.
    Simple is better than complex.
    Complex is better than complicated.
    Flat is better than nested.
    Sparse is better than dense.
    Readability counts.
    Special cases aren't special enough to break the rules.
    Although practicality beats purity.
    Errors should never pass silently.
    Unless explicitly silenced.
    In the face of ambiguity, refuse the temptation to guess.
    There should be one-- and preferably only one --obvious way to do it.
    Although that way may not be obvious at first unless you're Dutch.
    Now is better than never.
    Although never is often better than *right* now.
    If the implementation is hard to explain, it's a bad idea.
    If the implementation is easy to explain, it may be a good idea.
    Namespaces are one honking great idea -- let's do more of those!

                                       - Tim Peters, The Zen of Python

## Test related conventions

These are the conventions for tests that are written in ooniprobe. That is what
goes inside of nettests/.

### Naming

All methods that are relevant to the test should be all lower case separated by
underscore.

All variables that are specific to your test should be all lower case separated
by underscore.

### Simplicity

Tests written in ooniprobe should be as short as possible and should contain as
little code not related to the measurement as possible. It should be possible
from reading the test to understand what it does without clutter.

Everything that is not related directly to the test should go inside of the
test template of which the test you are writing is a subclass of.


## Style guide

This is an extract of the most important parts of PEP-8. When in doubt on
what code style should be followed first consult this doc, then PEP-8 and
if all fails use your best judgement or ask for help.

The most important part to read is the following as it contains the guidelines
of naming of variables, functions and classes, as it does not follow pure
PEP-8.

### Naming convention

Class names should follow the CapWords convention.
Note: When using abbreviations in CapWords, capitalize all the letters
      of the abbreviation.  Thus HTTPServerError is better than
      HttpServerError.

Exception names should follow the class names convention as exceptions
should be classes.

Method names should follow camelCase with the first letter non-capital.

Class attributes should also follow camelCase with the first letter non-capital.

Functions should follow camelCase with the first letter non-capital.

Functions and variables that are inside the local scope of a class or method
should be all lowercase separated by an underscore.

### Indentation

Use 4 spaces per indentation level.

    This can be setup in vi with:
        set tabstop=4
        set shiftwidth=4
        set expandtab


Continuation lines should be wrapped like this:

        foo = long_function_name(var_one, var_two,
                                 var_three, var_four)

or this:

        def long_function_name(var_one,
                    var_two, var_three,
                    var_four):
            print(var_one)


They should NOT be wrapped like this:

        foo = long_function_name(var_one, var_two,
                var_three, var_four)

and NOT like this:

        # See how it creates confusion with what is inside the function?
        def long_function_name(var_one,
            var_two, var_three,
            var_four):
            print(var_one)


### Tabs or Spaces?

Every time you insert a \t into any piece of code a kitten dies.

Only spaces. Please.

(code should be run with python -tt)

### Maximum Line Length

Maximum of 79 characters. 72 characters for long blocks of text is recommended.

### Blank Lines

Separate top-level function and class definitions with two blank lines.

Method definitions inside of class are separated by a single blank line.


### Encoding

Always use UTF-8 encoding. This can be specified by adding the encoding cookie
to the beginning of your python files:

    # -*- coding: UTF-8

All identifiers should be ASCII-only. All doc strings and comments should also
only be in ASCII. Non ASCII characters are allowed when they are related to
testing non-ASCII features or for the names of authors.


### Imports

Import should be one per line as so:

    import os
    import sys
    from subprocess import Popen, PIPE

Imports are always at the top of the file just after any module comments
and docstrings, berfore module globals and constants.

Imports should be grouped in the following order:

1. standard library imports
2. related third party imports
3. local application/library specific imports

You should put a blank line between each group of imports.


### Comments

Comments should always be up to date with the code. Don't have
comments that contraddict with the code.

Comments should always be written in English.

Blocks comments are indented to the same level of the code that
they refer to. They start with # and are followed by a single space.

Use inline comments sparingly. # Gotcha?


### Documentation strings

Write docstrings for all public modules, functions, classes and
methods. Even better if you write them also for non-public methods.

Place docstrings under the def.

For a better overview on how to write docstrings consult: PEP-257

