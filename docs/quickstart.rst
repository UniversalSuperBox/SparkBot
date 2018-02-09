Quickstart
==========

This document will lead you through the steps to run the base Sparkbot instance.

Get a token from Spark
----------------------

Head over to Cisco Spark for Developer's `My Apps portal`_ and click the Add button to create a new bot. Go through the steps to create a bot. Once you're finished, copy the Bot's Access Token somewhere safe. We'll need it later in this process.

Install required packages
-------------------------

First you'll need to install the prerequisites for running SparkBot with these instructions.

Ubuntu 16.04
^^^^^^^^^^^^

.. code-block:: shell

    sudo apt install python3 python3-virtualenv nginx

Clone the source
----------------

Clone the bot's source to the home directory of the user you will be running it as. I recommend creating a service account for your bot then using that.

From here on, we'll assume that the bot's source code is located in ``~/sparkbot``.

Copy run.py.example
-------------------

``run.py.example`` contains the code needed to run SparkBot. It's also where you'll create new commands for the bot. We'll copy it to ``run.py`` now::

    cp ~/sparkbot/run.py.example ~/sparkbot/run.py

Set up a virtualenv
-------------------

Create and activate a Python(3.4+) virtualenv for the bot::

    python3 -m virtualenv ~/sparkbotEnv
    source ~/sparkbotEnv/bin/activate

Now we can install the required Python packages::

    pip install -r ~/sparkbot/requirements.txt

Add nginx configuration
-----------------------

We'll use nginx to proxy requests to the bot. You may use this configuration as a template for your reverse proxy::

    server {
        listen 80;
        server_name [FQDN];
        root /var/www/default1;
        location / {
                proxy_pass http://localhost:8080/;
        }
    }

SparkBot assumes that it will be reachable over HTTPS. If you do not have a reverse proxy in front of your bot's server that will provide this for you, you will need to change these options to provide TLS.

Run the bot
-----------

We can now test the bot. Sparkbot requires that a few environment variables need to be set. Replace ``[url]`` below with the URL that points to your HTTPS endpoint without the protocol or trailing slashes (for example, enter ``127.0.0.1`` for ``https://127.0.0.1/``). Replace ``[api_token]`` with the token that Spark gave you for your bot::

    cd ~/sparkbot
    source ~/sparkbotEnv/bin/activate
    export SPARK_ACCESS_TOKEN=[api_token]
    export WEBHOOK_URL=[url]
    export RECEIVER_PORT=8080
    python run.py

The bot should now be running and, assuming your proxy is working correctly, be able to respond to requests directed at it from Spark. Try messaging the bot with ``ping`` or ``help`` to see if it will respond.

Auto-start with systemd
-------------------------------

You can set up the bot so that it runs when the computer boots up. To do that, we'll create and edit a systemd unit.

First, create the file ``/etc/systemd/system/sparkbot.service`` with the following content, then run ``systemctl daemon-reload``:

.. literalinclude:: /_static/sparkbot.service
   :caption: /etc/systemd/system/sparkbot.service

Next, run ``systemctl edit sparkbot.service`` and enter the following, changing the options in curly brackets to match your desired settings:

.. literalinclude:: /_static/sparkbot.service.edit
   :caption: systemctl edit sparkbot.service

Note that ``{USER}`` is the account which you used to clone the bot.

Once that's finished, run the following to enable the bot on startup::

    systemctl daemon-reload
    systemctl enable sparkbot
    systemctl start sparkbot

.. _my apps portal: https://developer.ciscospark.com/apps.html