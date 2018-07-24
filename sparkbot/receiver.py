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
from ciscosparkapi import CiscoSparkAPI, WebhookEvent, Room
from logging import Logger
import shlex
from types import GeneratorType
import functools

class ReceiverResource(object):

    def __init__(self, bot, teams_api):
        self.bot = bot
        self.me = self.bot.spark_api.people.me()
        self.teams_api = teams_api

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

        bot_thread = Thread(target=self.command_dispatcher, args=(self.teams_api, user_request,))
        bot_thread.start()

        return

    def command_dispatcher(self, user_request):
        """Executes a command on SparkBot ``bot`` for the user's request.

        This method is called by the receiver when a command comes in. It uses the information in
        the user_request to execute a command (using :meth:`execute_command`) and send its reply
        back to the user.

        :param bot: Bot which will execute this command
        :type bot: sparkbot.SparkBot

        :param user_request: Event where the user called the bot
        :type user_request: ciscosparkapi.WebhookEvent
        """

        room_id = user_request.data.roomId
        message = self.bot.spark_api.messages.get(user_request.data.id)
        caller = self.bot.spark_api.people.get(message.personId)

        # Catch any errors in the shlex string
        try:
            commandline = shlex.split(message.text)
        except ValueError as error:
            # Something is incorrect in the user's command string
            if isinstance(self.bot._logger, Logger):
                self.bot._logger.exception(' '.join([caller.emails[0], 'caused:', error.args[0],
                                                'with the message:', message.text]))
            response = ' '.join(["⚠️Error: Please check the format of your command.",
                                            error.args[0]])
            #TODO: Send a spark message here with response

        # Remove my name from the beginning of the message if it's there
        my_name = self.bot.me.displayName
        if commandline[0] == my_name:
            del commandline[0]

        userfunc_torun = str.lower(commandline[0])


        response = self.bot.execute_command(userfunc_torun, commandline=commandline,
                                    event=user_request, caller=caller, room_id=room_id)

        if isinstance(response, str):
            self.send_spark_message(room_id, response)
        elif isinstance(response, GeneratorType):
            for response in response:
                self.send_spark_message(room_id, response)

    def send_spark_message(self, spark_room, markdown):
        """Sends a message to a Teams room.

        :param markdown: Markdown formatted string to send

        :param spark_room: The room that we should send this response to
        :type spark_room: ciscosparkapi.Room or str

        """
        if not markdown or not isinstance(markdown, str):
            raise ValueError("response must be a non-blank string.")

        if isinstance(spark_room, Room):
            self.teams_api.messages.create(spark_room.id, markdown=markdown)
        if isinstance(spark_room, str):
            self.teams_api.messages.create(spark_room, markdown=markdown)

def create(bot, teams_api):
    """Creates a falcon.API instance with the required behavior for a SparkBot receiver.

    Currently the API webhook path is hard-coded to ``/sparkbot``

    :param bot: :class:`sparkbot.SparkBot` instance for this API instance to use
    """

    if not isinstance(teams_api, CiscoSparkAPI):
        raise TypeError("spark_api is not of type ciscosparkapi.CiscoSparkAPI")

    api = falcon.API()
    api_behavior = ReceiverResource(bot, teams_api)
    api.add_route("/sparkbot", api_behavior)

    return api

def random_bytes(length):
    """ Returns a random bytes array with uppercase and lowercase letters, of length length"""
    cryptogen = SystemRandom()
    my_random_string = ''.join([cryptogen.choice(string.ascii_letters) for _ in range(length)])
    my_random_bytes = my_random_string.encode(encoding='utf_8')

    return my_random_bytes

