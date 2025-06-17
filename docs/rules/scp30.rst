.. _scp30:

===========================
SCP30: Wrong setting getter
===========================

What it does
============

Finds cases where the getter (or subscript, ``[]``) used to read a setting does
not match the known setting type.


Why is this bad?
================

Scrapy settings may be defined in contexts outside Python, e.g. on the command
line where only string values can be specified, so the right getter must be
used to get the right value.

Using the wrong getter can lead to type errors or unexpected behavior.


Example
=======

.. code-block:: python

    settings["RETRY_TIMES"]

Use instead:

.. code-block:: python

    settings.getint("RETRY_TIMES")
