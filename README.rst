sparkbot
========

sparkbot makes it easy to create your own chatbot for Cisco Spark.

It provides a low barrier to entry:

#. Install the package: ``pip install git+https://github.com/universalsuperbox/sparkbot.git``
#. Use ``run.py.example`` to make a script that adds your commands and runs the bot.
#. Set up a reverse proxy that provides HTTPS (nginx and Let's Encrypt make it 
   easy)
#. Start ``run.py``

For more information, see `the documentation`_.

Features
--------

- Some Assembly Required: sparkbot doesn't handle HTTPS or proxying. Use what 
  **you** want for that.
- Complete Flexibility: You can do whatever you want in your commands as long as you return a string
  as a reply to the user.

Build the documentation
-----------------------

To build the documentation, cd into the ``doc`` folder and run the following::

    pip install -r requirements-dev.txt
    make html

If you are on Windows, use ``make.bat`` rather than ``make``.

The documentation will be located in the ``doc/_build/`` directory.

Contribute
----------

To develop on sparkbot, you can do the following::

    pip install -r requirements-dev.txt
    pip install -e .

When you're ready to commit, run the bot's tests first. You will need a copy of `nodejs`_ installed, then run the following::

    pytest

Support
-------

If you experience issues with sparkbot, please visit the issue tracker.

License
-------

Sparkbot is copyright Dalton Durst, 2018. It is licensed under the Apache license, version 2.0. See the LICENSE file for more details.

.. _the documentation: http://sparkbot.readthedocs.io/en/latest/
.. _nodejs: https://nodejs.org/en/download/
