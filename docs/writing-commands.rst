Writing Commands
================

Introduction
------------

SparkBot provides a very simple interface for writing commands. You will be familiar with it if you have ever used Flask. Here's a simple ``ping`` command::

    @MY_BOT.command("ping")
    def ping(caller):
        """
        Checks if the bot is running.

        Usage: `ping`

        Returns **pong**.
        """

        return "**pong**"

Let's break down what's happening here line-by-line.

First, we have the decorator, :func:`sparkbot.core.SparkBot.command`, which marks this function as a command for our bot:

.. code-block:: python

    @MY_BOT.command("ping")

``bot`` is the SparkBot instance that we're adding this command to. ``"ping"`` is what we want the user to type in order to invoke this command.

Next, the function definition and docstring:

.. code-block:: python

    def ping():
        """
        Usage: `ping`

        Returns **pong**.
        """

The docstring also serves as the command's help, accessible via the ``help [command]`` command. It must all be equally spaced (so don't put the description on the same line as the opening quotes like you would in most cases) and is formatted in Markdown. You should stick to the general format of description, usage, returns when writing your docstrings for commands.

.. figure:: /_static/writing-commands/SparkBot-wc-2.PNG
   :alt: Using 'help ping'
   :scale: 65%

Finally, we see how simple it is to send `formatted text`_ back to the user:

.. code-block:: python

    return "**pong**"

When we add this to the area below the ``# Add commands here`` comment and re-run the bot, we can now use the ``ping`` command:

.. figure:: /_static/writing-commands/SparkBot-wc-1.PNG
   :alt: Using the 'ping' command
   :scale: 65%

.. _arguments:

Taking arguments
----------------

In many cases you will want to take arguments to your commands. Sparkbot uses `shlex.split`_ to split the message sent by the user into multiple 'tokens' that are given to you in a list. These tokens are split in a similar way to a POSIX shell.

Here's a command that uses this type of input. It simply returns the first token in the list:

.. code-block:: python

    @MY_BOT.command("testcommand")
    def testcommand(commandline):
        """
        Usage: `testcommand something`

        A command used for testing. Returns the first word you typed.
        """

        if commandhelpers.minargs(1, commandline):
            return commandline[1]
        else:
            return 'This command requires at least one argument'

While the help says that this will only return the first word, this command will also return the first quoted string that's typed as well.

.. figure:: /_static/writing-commands/SparkBot-wc-testcommand.PNG
   :alt: Using the 'testcommand' command from above
   :scale: 65%

Let's go over this line-by-line:

.. code-block:: python
   :emphasize-lines: 2

    @MY_BOT.command("testcommand")
    def testcommand(commandline):

As usual, we use the :func:`sparkbot.core.SparkBot.command` decorator to add this function to our bot's list of commands. However, notice that we defined the function to take the argument ``commandline``. This is one of several keywords that SparkBot recognizes. When executing your function, it will find this keyword and send the ``commandline`` property accordingly.

When the user types ``testcommand some cool stuff``, this code receives the following list as its ``commandline`` argument::

    ['testcommand', 'some', 'cool', 'stuff']

Whereas ``testcommand "some cool" stuff`` will yield the following::

    ['testcommand', 'some cool', 'stuff']

Using a helper function, :func:`sparkbot.commandhelpers.minargs`, we check to make sure we have at least one argument (token) in the commandline. Then, we return either the first token if there is one or more, or an error if there are no tokens::

    if commandhelpers.minargs(1, commandline):
        return commandline[1]
    else:
        return 'This command requires at least one argument'

As you can see, you can quickly create a CLI-like interface by iterating over the tokens in this list.

.. _early-reply:

Replying early
--------------

If a command will be running for a very long time, you may want to notify the user of its progress. SparkBot recognizes a ``callback`` keyword that gives you access to a callback function. You may use this callback function to send a message in the room where the user called the bot. We'll see an example of this in the following function:

.. code-block:: python
   :emphasize-lines: 9

    @MY_BOT.command("ping")
    def ping_callback(callback, room_id):
        """
        Usage: `ping`

        Returns **pong**, but with a twist.
        """

        callback("a twist.")

        return '**pong**'

.. figure:: /_static/writing-commands/SparkBot-wc-replyEarly.PNG
   :alt: Using the ping command with an interim response
   :scale: 65%

List of recognized keywords
---------------------------

==============  ====
Keyword         Data
==============  ====
commandline     List containing user's message split into tokens by `shlex.split`_. :ref:`arguments`
event           Dictionary containing the `event request`_ from Spark.
caller          `ciscosparkapi.Person`_ for the user that called this command
callback        Function that can be used to reply to the user that called this command. :ref:`early-reply`
room_id         ``Str`` containing the ID of the room where this command was called
==============  ====

.. _formatted text: https://developer.ciscospark.com/formatting-messages.html
.. _shlex.split: https://docs.python.org/3.5/library/shlex.html#shlex.split
.. _event request: https://developer.ciscospark.com/webhooks-explained.html#handling-requests-from-spark
.. _ciscosparkapi.Person: http://ciscosparkapi.readthedocs.io/en/latest/user/api.html#person