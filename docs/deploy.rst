Deploy
======

When it comes time to deploy your bot to a server, we recommend using gunicorn and nginx. The following information will help you run the bot under gunicorn with nginx as its reverse proxy.

This information is adapted from the `Deploying Gunicorn`_ document, you may wish to head to it for more advanced setups.

Install required system packages
--------------------------------

Before starting, it is important to have ``nginx`` and the appropriate Python 3 packages installed.

Ubuntu 16.04 / 18.04
""""""""""""""""""""

::

    sudo apt install nginx python3 python3-pip python3-virtualenv

Install Python packages in a virtualenv
---------------------------------------

Create a virtualenv for SparkBot with the required packages. This will keep system-level Python packages separate from your SparkBot packages.

It's a good idea to create a new service account with the bare minimum permissions for Sparkbot::

    sudo useradd --system --create-home sparkbot

Now, log in to the sparkbot user so we can install the virtualenv::

    sudo -Hu sparkbot /bin/bash

Finally, create the virtualenv and install SparkBot into it::

    python3 -m virtualenv --python=python3 /home/sparkbot/sparkbotenv
    source /home/sparkbot/sparkbotenv/bin/activate
    pip install git+https://github.com/universalsuperbox/SparkBot.git gunicorn
    deactivate
    exit

Get your run.py script
----------------------

This guide assumes that your SparkBot script is called ``run.py`` and is placed at ``/home/sparkbot/run.py``. If your script is named differently, change ``run`` in ``run:bot.receiver`` in the ``ExecStart`` entry to the script's name (without ``.py``). If your script is located in a different directory, change the WorkingDirectory.

Add nginx configuration
-----------------------

We'll use nginx to proxy requests to the bot. You may use this configuration as a template for your reverse proxy for the bot's webhook receiver:

.. literalinclude:: /_static/sparkbot-nginx.conf
   :caption: /etc/nginx/conf.d/sparkbot.conf

Remember to set the ``server_name`` property to the FQDN of your server.

It is highly recommended to use HTTPS for this reverse proxy, but setting that up is outside of the
scope of this guide.

Auto-start with systemd
-----------------------

First, we'll add a unit file for the Gunicorn socket. This goes at ``/etc/systemd/system/sparkbot.socket``:

.. literalinclude:: /_static/sparkbot.socket
   :caption: /etc/systemd/system/sparkbot.socket

Next, create the file ``/etc/systemd/system/sparkbot.service`` with the following content. Once finished, save and close the file then run ``systemctl daemon-reload``:

.. literalinclude:: /_static/sparkbot.service
   :caption: /etc/systemd/system/sparkbot.service

Next, run ``systemctl edit sparkbot.service`` and enter the following, changing the options in curly brackets to match your desired settings:

.. literalinclude:: /_static/sparkbot.service.edit
   :caption: systemctl edit sparkbot.service

The values should be the same as the ones you used when you followed :doc:`the Quickstart guide </quickstart>`.

Once that's finished, run the following to enable the bot on startup::

    sudo systemctl daemon-reload
    sudo systemctl enable sparkbot.socket
    sudo systemctl enable sparkbot.service
    sudo systemctl start sparkbot.socket
    sudo systemctl start sparkbot.service

.. _deploying gunicorn: http://docs.gunicorn.org/en/stable/deploy.html
