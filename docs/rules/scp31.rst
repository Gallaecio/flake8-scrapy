.. _scp31:

===========================
SCP31: Unneeded setting get
===========================

What it does
============

Finds calls to :meth:`~scrapy.settings.BaseSettings.get` on settings objects
with a single parameter.


Why is this bad?
================

In Scrapy, there is no functional difference between ``settings["FOO"]`` and
``settings.get("FOO")``. Both will return the setting value if it exists, or
``None`` if it doesn't.

The subscript notation ``settings["FOO"]`` is preferred for readability and
consistency with standard Python dictionary access patterns.

The :meth:`~scrapy.settings.BaseSettings.get` method should only be used when
you need to provide a default value, i.e.,
``settings.get("FOO", default_value)``.


Example
=======

.. code-block:: python

    settings.get("BOT_NAME")

Use instead:

.. code-block:: python

    settings["BOT_NAME"]
