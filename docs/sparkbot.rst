SparkBot API
============

Submodules
----------

sparkbot\.core module
^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: sparkbot.core.SparkBot
    :members:
    :undoc-members:
    :show-inheritance:
    :exclude-members: my_help_all, my_help

    .. method:: my_help_all

       Returns a markdown-formatted list of commands that this bot has. Command, meant to be called
       by a bot user. Called by a user by typing "help", "help all", or "help-all".

    .. method:: my_help(commandline)

       Returns the help of the command given in ``commandline``. Command, meant to be called by a
       bot user. Calls :func:`my_help_all()` if no command ("") is given or is ``all``. Called by
       a user by typing ``help``.

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
