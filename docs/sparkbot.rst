API Documentation
=================

This page contains information about SparkBot's internals. Bot authors may not find it terribly useful, SparkBot hackers will.

SparkBot
--------

.. autoclass:: sparkbot.SparkBot
    :members:
    :undoc-members:
    :show-inheritance:
    :exclude-members: my_help_all, my_help

    .. method:: my_help_all

       Returns a markdown-formatted list of commands that this bot has. This function is used by the default "help" command to show the full list.

    .. method:: my_help(commandline)

       Returns the help of the command given in ``commandline``. Calls :meth:`my_help_all()` if no command is given or is ``all``. Called by a user by typing ``help``. This function is the default "help" command and can be removed using :meth:`remove_help()`.

Default receiver
----------------

The receiver waits for a request from Webex Teams and executes :meth:`sparkbot.SparkBot.command_dispatcher` when one comes in.

.. automodule:: sparkbot.receiver
    :members:
    :undoc-members:
    :show-inheritance:
