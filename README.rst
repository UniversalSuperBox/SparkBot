########
SparkBot
########

What is SparkBot?
=================

In short, SparkBot is the spark that makes your Cisco Webex Teams bots come to life.

SparkBot is Simple
------------------

.. code-block:: python

    from ciscosparkapi import CiscoSparkAPI
    from sparkbot import SparkBot

    spark_api = CiscoSparkAPI()
    bot = SparkBot(spark_api)

    @bot.command("ping")
    def ping(caller):
        return (caller.nickName, ", pong")

SparkBot provides a simple way to interface with Webex Teams. Its purpose is to take you from zero to talking on Teams as quickly as possible. You'll need to provide an HTTPS endpoint using your software of choice, then you're off to the races.

SparkBot has exactly what you need
----------------------------------

SparkBot includes its own request dispatcher which takes your users' messages and routes them into the correct commands. It does this by parsing their message like a shell processor. You can choose to take as much or as little information about the request as you need for each command.

SparkBot also includes a default "help" command to list its available commands and show users how to use them.

Oh, and if you don't want any of that, you can get rid of it all and do it yourself.

SparkBot gets out of your way
-----------------------------

SparkBot isn't integrated with a machine learning platform, stuffed into a natural language processing framework, and bundled into a cloud provider. It isn't going to try to wrangle you into a hosting contract or keep you locked in to any vendor. No commitments or learning curves.

How do I get it?
================

You can install SparkBot from PyPI::

    pip install SparkBot

Now that you've got it, head over to `the documentation`_ to get started!

What do I need to know about the beta?
======================================

SparkBot currently *does not provide* a stable API. The way to run and develop SparkBot may change
before it reaches a 1.0.0 release. The interface for writing commands is expected to be stable, but
that is not guaranteed. See the `SparkBot 1.0.0`_ milestone for the features and bugs that must be
resolved before that release.

How do I get support?
=====================

If you experience issues with SparkBot, please visit the issue tracker.

How can I contribute?
=====================

Thanks for asking! Here's how you can test the SparkBot code or build its documentation locally:

Test the code
-------------

To develop on SparkBot, you can do the following::

    pip install -e .[dev]

When you're ready to commit, run the bot's tests first. You will need a copy of `nodejs`_ installed,
then run the following::

    pytest

Build the documentation
-----------------------

To build the documentation, cd into the ``doc`` folder and run the following::

    pip install -e ../[dev]
    make html

If you are on Windows, use ``make.bat`` rather than ``make``.

The documentation will be located in the ``doc/_build/`` directory.

License
-------

SparkBot is copyright Dalton Durst, 2018. It is licensed under the Apache license, version 2.0. See
the LICENSE file for more details.

.. _the documentation: http://sparkbot.readthedocs.io/en/latest/
.. _sparkbot 1.0.0: https://github.com/UniversalSuperBox/SparkBot/milestone/1
.. _nodejs: https://nodejs.org/en/download/
