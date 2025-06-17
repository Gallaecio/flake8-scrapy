.. _scp29:

===================================
SCP29: No-op setting getter default
===================================

What it does
============

Finds calls to setting getter methods
(:meth:`~scrapy.settings.BaseSettings.get`,
:meth:`~scrapy.settings.BaseSettings.getbool`, etc.) where a redundant default
value is provided.


Why is this bad?
================

It is dead code.


Example
=======

.. code-block:: python

    settings.getint("RETRY_TIMES", 10)
    settings.get("FOO", None)
    settings.getbool("BAR", False)

| :setting:`RETRY_TIMES` defaults to 2, 10 is ignored.
| ``get()`` and ``getbool()`` already returns those defaults.

Use instead:

.. code-block:: python

    settings.getint("RETRY_TIMES")
    settings["FOO"]
    settings.getbool("BAR")
