"""The nuts and bolts of sparkbot"""

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

from .exceptions import CommandNotFound, SparkBotError, CommandSetupError
from . import receiver
import shlex
import textwrap
import functools
from types import FunctionType, GeneratorType
from logging import Logger
from inspect import signature
from os import environ
import falcon
from ciscosparkapi import CiscoSparkAPI, Webhook, Room

class SparkBot:
    """ A bot for Cisco Webex Teams

    SparkBot automatically creates a webhook for itself and will delete any other webhooks on its
    bot account. To do this, it uses the ``root_url`` parameter or ``WEBHOOK_URL`` in the
    environment to know its public URL.

    SparkBot has a ``help`` command built in by default. These may be overridden using the
    :func:`command` decorator and providing the "help" argument and a function with your desired
    behavior on calling ``help``. See :doc:`Writing Commands </writing-commands>` for more
    information on writing commands.

    :param spark_api: CiscoSparkAPI instance that this bot should use
    :type spark_api: ciscosparkapi.CiscoSparkAPI

    :param root_url: The base URL for the SparkBot webhook receiver. May also be provided as
                     ``WEBHOOK_URL`` in the environment.
    :type root_url: str

    :param logger: Logger that the bot will output to
    :type logger: logging.Logger
    """

    def __init__(self, spark_api, root_url=None, logger=None):

        if isinstance(spark_api, CiscoSparkAPI):
            self.spark_api = spark_api
        else:
            raise TypeError("spark_api is not of type ciscosparkapi.CiscoSparkAPI")

        if isinstance(logger, Logger):
            self._logger = logger
        elif logger:
            # There is a value for logger, but it isn't a Logger
            raise TypeError("logger is not of type logging.Logger")
        else:
            self._logger = None

        self.commands = {}
        self.commands["help"] = Command(self.my_help)
        self.fallback_command = None

        # Message sent to user when they request a command that doesn't exist.
        self.command_not_found_message = "Command not found. Maybe try 'help'?"

        # Cache "me" to speed up commands requiring it
        self.me = self.spark_api.people.me()

        # The output of the "help all" command should only need to be determined once.
        # See self.my_help_all to learn more.
        self._help_all_string = ""

        if not root_url:
            try:
                root_url = environ["WEBHOOK_URL"]
            except KeyError:
                if self._logger:
                    self._logger.warn(("SparkBot instanced without a webhook URL argument. This is "
                                       "done in the test suite, but is generally not advisable for "
                                       "normal use."))
        elif not isinstance(root_url, str):
            raise TypeError("root_url is not of type str")

        # Create my receiver
        self.webhook_secret = receiver.random_bytes(32)
        self.receiver = receiver.create(self)

        # Create my webhook
        if root_url:

            if root_url.startswith("http:"):
                if self._logger:
                    self._logger.warn(("Creating SparkBot with http-only webhook. This is not "
                                       "recommended. Please use an HTTPS webhook to better secure "
                                       "your users' data."))

            for webhook in self.spark_api.webhooks.list():
                self.spark_api.webhooks.delete(webhook.id)
            self.spark_api.webhooks.create("myBot",
                                           root_url + "/sparkbot",
                                           "messages",
                                           "created",
                                           secret=self.webhook_secret.decode())

    def command(self, command_strings=[], fallback=False):
        """ Decorator that adds a command to this bot.

        :param command_strings: Callable name(s) of command. When a bot user types this (these),
                                they call the decorated function. Pass a single string for a single
                                command name. Pass a list of strings to give a command multiple
                                names.
        :type command_strings: list
        :type command_strings: str


        :param fallback: False by default, not required. If True, sets this command as a
                         "fallback command", used when the user requests a command that does not
                         exist.
        :type fallback: bool

        :raises CommandSetupError: Arguments or combination of arguments was incorrect.
                                   The error description will have more details.

        :raises TypeError: Type of arguments was incorrect.

        """

        if not command_strings and not fallback:
            raise CommandSetupError("command_strings not given (or empty) in call to SparkBot.command, and this is not a fallback command. At least one command name is required in your decorator.")
        elif isinstance(command_strings, FunctionType):
            raise CommandSetupError("command_strings not given in call to SparkBot.command. Did you include the parentheses in your decorator?")

        def decorator(function):
            if isinstance(command_strings, str):
                names_to_register = [command_strings]
            elif isinstance(command_strings, list):
                names_to_register = command_strings
            else:
                raise TypeError("command_strings is not a str or list of str.")

            if not isinstance(fallback, bool):
                raise TypeError("fallback not a boolean in call to SparkBot.command. Do you have too many arguments in your decorator?")

            new_command = Command(function)

            if self.fallback_command:
                # There is already a fallback command
                raise CommandSetupError("Attempted to add a fallback command when one already exists.")

            # Register new command object under each of its names
            if fallback:
                self.fallback_command = new_command
            else:
                for command in names_to_register:
                    if not isinstance(command, str):
                        raise TypeError("non-str object found in command_strings.")

                    self.commands[command] = new_command

            return function

        return decorator

    def commandworker(self, json_data):
        """Called by the bottle app when a command comes in. Glues together the behavior of SparkBot.

        :param json_data: The blob of json that Spark POSTs to the webhook parsed into a dictionary
        """

        webhook_obj = Webhook(json_data)
        room_id = json_data["data"]["roomId"]
        message = self.spark_api.messages.get(webhook_obj.data.id)
        person = self.spark_api.people.get(message.personId)

        # Catch any errors in the shlex string
        try:
            commandline = shlex.split(message.text)
        except ValueError as error:
            # Something is incorrect in the user's command string
            if isinstance(self._logger, Logger):
                self._logger.exception(' '.join([person.emails[0], 'caused:', error.args[0],
                                                'with the message:', message.text]))
            errordescription = ' '.join(["⚠️Error: Please check the format of your command.",
                                         error.args[0]])
            self.respond(room_id, errordescription)
            return

        # Remove my name from the beginning of the message if it's there
        my_name = self.me.displayName
        if commandline[0] == my_name:
            del commandline[0]

        userfunc_torun = str.lower(commandline[0])

        # Catch generic Exception so that we always reply to the user.
        try:
            usercommandresponse = self._executeuserfunction(userfunc_torun, commandline,
                                                            webhook_obj, person, room_id)
        except Exception as error:

            # Build our logging string
            if isinstance(self._logger, Logger):
                self._logger.exception(' '.join([person.emails[0], 'caused:', type(error).__name__,
                                                error.args[0], 'with the command:', message.text]))
            try:
                errordescription = error.args[1]
            except IndexError:
                errordescription = ("Something happened internally. "
                                    "For more information, contact the bot author.")
            # Make response
            finalresponse = " ".join(["⚠️ Error:", errordescription])

        else:
            finalresponse = usercommandresponse

        # finalresponse will be a Generator if the executed function contains the yield keyword.
        if isinstance(finalresponse, str):
            self.respond(room_id, finalresponse)
        elif isinstance(finalresponse, GeneratorType):
            for response in finalresponse:
                self.respond(room_id, response)

    def remove_help(self):
        """Removes the help command from the bot

        This will remove the help command even if it has been overridden.
        """

        self.command_not_found_message = "Command not found."
        self.commands.pop("help", None)

    def _executeuserfunction(self, func, commandline, event_json_dict, caller, room_id):
        """Runs the bot user's specified command (found in func) if it exists.

        :param func: The 'command' that the user wants to run. Should match a command string
                     that has previously been added to the bot.

        :param commandline: The user's complete message to the bot parsed into a list of tokens
                            by ``shlex.split()``.

        :param event_json_dict: The blob of JSON that Spark gives us in the webhook, parsed into
                                a ``dict``.

        :param caller: The user who sent the message we're processing. Must be
                       of type ciscosparkapi.Person.

        :param room_id: The ID of the room that the message we're processing was sent in.
        """

        command_to_run = None

        # Try to find command in the commands dictionary
        if func in self.commands:
            command_to_run = self.commands[func]
        elif self.fallback_command:
            command_to_run = self.fallback_command
        else:
            raise CommandNotFound('No command found', self.command_not_found_message)

        # To add a new argument for commands to use, have them sent into this function by
        # commandworker. Then, add them here and to the signature of Command.execute()
        return command_to_run.execute(commandline=commandline,
                                      callback=self.respond,
                                      event=event_json_dict,
                                      caller=caller,
                                      room_id=room_id)

    def respond(self, spark_room, markdown):
        """Sends a message to a Spark room.

        :param markdown: Markdown formatted string to send

        :param spark_room: The room that we should send this response to,
            either CiscoSparkAPI.Room or str containing the room ID

        """
        if not markdown or not isinstance(markdown, str):
            raise ValueError("response must be a non-blank string.")

        if isinstance(spark_room, Room):
            self.spark_api.messages.create(spark_room.id, markdown=markdown)
        if isinstance(spark_room, str):
            self.spark_api.messages.create(spark_room, markdown=markdown)

    def my_help(self, commandline):
        """
        The default help command.

        Usage: `help [command]`

        Gives the help for [command]. If a command is not given (or is `all`), gives `help-all`.
        """

        try:
            command_to_help = commandline[1]
        except IndexError:
            # The user did not specify a command to get help on. Return the "help-all" command.
            return self.my_help_all()

        if str.lower(command_to_help) == "all":
            return self.my_help_all()

        try:
            help_text_raw = self.commands[command_to_help].function.__doc__
            help_text = textwrap.dedent(help_text_raw)
        except KeyError:
            # The requested command doesn't exist
            help_text = "I don't have a command with the name \"{}\".".format(command_to_help)
        except TypeError:
            # The requested command doesn't have a docstring
            help_text = "There is no help available for `{}`.".format(command_to_help)

        return help_text

    def my_help_all(self):
        """Returns a formatted list of all commands for this bot"""

        # Create a formatted string containing all of our commands
        # One command can have multiple names and therefore takes up multiple slots in the
        # self.commands dict. However, for this help, we want multiple names for one command
        # to be grouped together. In this process, we'll look at every command added to this bot
        # and group together ones which are the same.
        # We can't add or remove commands after the bot starts, so we can create this string once
        if not self._help_all_string:
            temp_command_list = []
            used_command_string_list = []

            # Iterate over all of our commands to obtain a list where multiple
            # names for one command are in the same entry.
            for command_string, command_object in self.commands.items():

                if command_string in used_command_string_list:
                    continue

                used_command_string_list.append(command_string)
                current_command_strings = [command_string]

                # Iterate over the commands *again* and put any names for commands that
                # match the one we're currently checking into current_command_strings
                for inner_command_string, inner_command_object in self.commands.items():
                    if inner_command_object == command_object and command_string != inner_command_string:
                        used_command_string_list.append(inner_command_string)
                        current_command_strings.append(inner_command_string)

                temp_command_list.append(", ".join(sorted(current_command_strings)))

            sorted_commands = sorted(temp_command_list)

            output = ("Type `help [command]` for more specific help about any of these commands:\n - "
                    + "\n - ".join(sorted_commands))

            self._help_all_string = output

        return self._help_all_string

class Command:
    """ Represents a command that can be executed by a SparkBot

    :param function: The function that this command will execute. Must return a str.
    """

    def __init__(self, function):
        self.function = function

    @classmethod
    def create_callback(self, respond, room_id):
        """ Pre-fills room ID in the function given by ``respond``

        Adds the room ID as the first argument of the function given in ``respond``, simplifying the
        'callback' experience for bot developers.

        :param respond: The method to add the room ID to

        :param room_id: The ID of the room to preset in ``respond``
        """

        callback = functools.partial(respond, room_id)
        callback.__doc__ = ("SparkBot.respond method with room_id pre-filled, call this with ",
                            "the message you would like to reply inside the called room with.")
        return callback


    def execute(self, commandline=None, event=None, caller=None, callback=None, room_id=None):
        """ Executes this command's ``function``

        Executes this Command's target function using the given parameters as needed. All
        parameters are required for normal function, named parameters are used for ease of
        understanding of the written code.

        :param commandline: ``shlex.split()``-processed list of tokens which make up the bot user's
                            message

        :param event: The webhook event that was sent to us by Webex Teams

        :param caller: The Person who pinged the bot to start this process

        :type caller: ciscosparkapi.Person

        :param callback: Function to be used as a callback. :func:`Command.create_callback()` is
                         used to turn this into a partial function, so the first argument of this
                         function must be a Spark room ID that the bot author will expect to act on.

        :param room_id: The ID of the room that the bot was called in

        :returns: str,  the desired reply to the bot user

        """

        possible_parameters = locals()

        function_parameters = signature(self.function).parameters
        parameters_to_pass = {}
        for parameter, value in possible_parameters.items():
            if parameter in list(function_parameters.keys()):
                parameters_to_pass[parameter] = value

        # Only create the callback function if it's needed
        if "callback" in parameters_to_pass:
            parameters_to_pass["callback"] = self.create_callback(callback, room_id)

        return self.function(**parameters_to_pass)
