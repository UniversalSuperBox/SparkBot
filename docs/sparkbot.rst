SparkBot API
============

Submodules
----------

SparkBot
^^^^^^^^

.. autoclass:: sparkbot.SparkBot
    :members:
    :undoc-members:
    :show-inheritance:
    :exclude-members: my_help_all, my_help

    .. method:: my_help_all

       Returns a markdown-formatted list of commands that this bot has. This function is used by the default "help" command to show the full list.

    .. method:: my_help(commandline)

       Returns the help of the command given in ``commandline``. Calls :func:`my_help_all()` if no command is given or is ``all``. Called by a user by typing ``help``. This function is the default "help" command and can be removed using :meth:`remove_help()`.

.. autoclass:: sparkbot.core.Command
    :members:
    :undoc-members:
    :show-inheritance:

sparkbot\.receiver module
^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: sparkbot.receiver
    :members:
    :undoc-members:
    :show-inheritance:

sparkbot\.commandhelpers module
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: sparkbot.commandhelpers
    :members:
    :undoc-members:
    :show-inheritance:

Module contents
---------------

.. automodule:: sparkbot
    :members:
    :undoc-members:
    :show-inheritance:
