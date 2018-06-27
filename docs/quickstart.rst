Quickstart
==========

This document will lead you through the steps to run the base Sparkbot instance.

Get a token from Webex Teams
----------------------------

Head over to Cisco Webex Teams for Developer's `My Apps portal`_ and click the Add button to create a new bot. Go through the steps to create a bot. Once you're finished, copy the Bot's Access Token somewhere safe. We'll need it later in this process.

Dependencies
------------

First you'll need to install the prerequisites for running SparkBot.

SparkBot requires the following software:

* Python 3.5 or higher
* Reverse proxy, such as nginx, for its webhook receiver. We'll be using `ngrok`_ in this quickstart.

Ubuntu 16.04
^^^^^^^^^^^^

To install the prerequisites on Ubuntu 16.04::

    sudo apt install python3 python3-virtualenv python3-pip nginx

Clone the source
----------------

Clone the bot's source to your desired location. From here on, we'll assume that the bot's source code is located in ``~/sparkbot``, but you can change the path as you need.

Copy run.py.example
-------------------

``run.py.example`` contains the code needed to run SparkBot. It's also where you'll create new commands for the bot. We'll copy it to ``run.py`` now::

    cp ~/sparkbot/run.py.example ~/sparkbot/run.py

Set up a virtualenv
-------------------

Create and activate a Python(3.5+) virtualenv for the bot::

    python3 -m virtualenv ~/sparkbotEnv
    source ~/sparkbotEnv/bin/activate

Now we can install the required Python packages::

    pip install -r ~/sparkbot/requirements.txt
    pip install gunicorn

Use ngrok for a temporary reverse proxy
---------------------------------------

`ngrok`_ is a great service for setting up temporary public URLs. We'll be using it to quickly test
our bot configuration. `Download ngrok`_, then run ``ngrok http 8000`` to get it running.

Run the bot
-----------

We can now test the bot. Sparkbot requires that a few environment variables be set, so we'll ``export`` them before we run::

    cd ~/sparkbot
    source ~/sparkbotEnv/bin/activate
    export SPARK_ACCESS_TOKEN=[api_token]
    export WEBHOOK_URL=[url]
    gunicorn run:bot.receiver

Replace ``[url]`` with the URL that points to your webhook endpoint. Since we're using ngrok, put the ``https`` Forwarding URL here. Replace ``[api_token]`` with the token that Webex Teams gave you for your bot.

The bot should now be running and, assuming your proxy is working correctly, be able to receive requests directed at it from Webex Teams. Try messaging the bot with ``ping`` or ``help`` to see if it will respond.

Next steps
----------

Now that you've got the bot running, you may want to learn more about :doc:`/writing-commands` or :doc:`Deploying SparkBot </deploy>`

.. _my apps portal: https://developer.webex.com/apps.html
.. _ngrok: https://ngrok.com/
.. _download ngrok: https://ngrok.com/download
