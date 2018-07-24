# Copyright 2018 Dalton Durst
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from threading import Thread
import hmac
import hashlib
import json
from random import SystemRandom
import string
import falcon
from ciscosparkapi import CiscoSparkAPI, WebhookEvent

class ReceiverResource(object):

    def __init__(self, bot):
        self.bot = bot
        self.me = self.bot.spark_api.people.me()

    def on_post(self, req, resp):
        """Receives messages and passes them to the sparkbot instance in BOT_INSTANCE"""

        resp.status = falcon.HTTP_204

        if not self.bot:
            resp.status = falcon.HTTP_500
            return

        if not req.content_length:
            resp.status = falcon.HTTP_400
            resp.body = "Missing command"
            return

        raw_response_body = req.bounded_stream.read()
        json_data = json.loads(raw_response_body.decode("utf-8"))

        if self.bot.webhook_secret:

            try:
                # Get the HMAC of the incoming message
                expected_digest = req.get_header("X-SPARK-SIGNATURE")
            except KeyError:
                # We expected but didn't receive a signature. Don't process any further.
                resp.status = falcon.HTTP_403
                return

            real_digest = hmac.new(self.bot.webhook_secret, msg=raw_response_body, digestmod=hashlib.sha1)
            if not hmac.compare_digest(real_digest.hexdigest(), expected_digest):
                # The received signature doesn't match the one we expect.
                resp.status = falcon.HTTP_403
                return

        # Loop prevention
        message_person_id = json_data["actorId"]
        if message_person_id == self.me.id:
            # Message was sent by me (bot); do not respond.
            return

        user_request = WebhookEvent(json_data)

        bot_thread = Thread(target=self.bot.command_dispatcher, args=(user_request,))
        bot_thread.start()

        return

def create(bot, **kwargs):
    """Creates a falcon.API instance with the required behavior for a SparkBot receiver.

    Currently the API webhook path is hard-coded to ``/sparkbot``

    :param bot: :class:`sparkbot.SparkBot` instance for this API instance to use

    :Keyword Arguments:
        Additional arguments may be used to specify more resources that should be exposed
        by the SparkBot receiver. For example, ``"/my_webhook"=[Falcon resource]`` will
        expose your Falcon resource at ``/my_webhook`` on the server.
    """

    api = falcon.API()
    api_behavior = ReceiverResource(bot)
    api.add_route("/sparkbot", api_behavior)

    for url, resource in kwargs.items():
        if url == "/sparkbot":
            raise ValueError("Cannot add resource to receiver with /sparkbot URL")

        api.add_route(url, resource)

    return api

def random_bytes(length):
    """ Returns a random bytes array with uppercase and lowercase letters, of length length"""
    cryptogen = SystemRandom()
    my_random_string = ''.join([cryptogen.choice(string.ascii_letters) for _ in range(length)])
    my_random_bytes = my_random_string.encode(encoding='utf_8')

    return my_random_bytes
