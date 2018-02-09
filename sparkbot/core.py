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

import shlex
import textwrap
import functools
from logging import Logger
from inspect import signature
from ciscosparkapi import CiscoSparkAPI, Webhook, Room

class SparkBot:
    """ A bot for Cisco Spark

    :param spark_api: CiscoSparkAPI instance that this bot should use
    :type spark_api: ciscosparkapi.CiscoSparkAPI

    :param logger: Logger that the bot will output to
    :type logger: logging.Logger
    """

    def __init__(self, spark_api, logger=None):

        if isinstance(spark_api, CiscoSparkAPI):
            self.spark_api = spark_api
        else:
            raise TypeError("spark_api is not of type ciscosparkapi.CiscoSparkAPI")

        if isinstance(logger, Logger):
            self.__logger__ = logger
        elif logger:
            # There is a value for logger, but it isn't a Logger
            raise TypeError("logger is not of type logging.Logger")

        self.commands = {}
        self.commands["help"] = Command(self.my_help)
        self.commands["help-all"] = Command(self.my_help_all)

        # Cache "me" to speed up commands requiring it
        self.me = self.spark_api.people.me()

    def command(self, command_strings):
        """ Decorator that adds a command to this bot.

        :param command_strings: Callable name(s) of command. When a bot user types this (these),
                                they call the decorated function. Pass a single string for a single
                                command name. Pass a list of strings to give a command multiple
                                names.
        """

        def decorator(function):
            if isinstance(command_strings, str):
                names_to_register = [command_strings]
            elif isinstance(command_strings, list):
                names_to_register = command_strings
            else:
                raise TypeError("command_strings is not a str or list of str.")

            new_command = Command(function)

            # Register new command object under each of its names
            for command in names_to_register:
                if not isinstance(command, str):
                    raise TypeError("command_strings is not a str or list of str.")

                self.commands[command] = new_command

            return function

        return decorator

    def commandworker(self, json_data):
        """Called by the Flask app when a command comes in. Glues together the behavior of bc3cb.

        :param json_data: The blob of json that Spark POSTs to the webapp, parsed into a
                          dictionary
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
            if isinstance(self.__logger__, Logger):
                self.__logger__.error(' '.join([person.emails[0], 'caused:', error.args[0],
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
            if isinstance(self.__logger__, Logger):
                self.__logger__.error(' '.join([person.emails[0], 'caused:', type(error).__name__,
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

        self.respond(room_id, finalresponse)

        return True

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
        else:
            raise Exception('BC3CBCommandNotFound', 'Command not found. Maybe try "help"?')

        # To add a new argument for commands to use, have them sent into this function by
        # commandworker and add them here to be passed to execute(). Then, add the new
        # variable to possible_parameters in the Command object.
        return command_to_run.execute(commandline=commandline, callback=self.respond,
                                      event=event_json_dict, caller=caller, room_id=room_id)


    def respond(self, spark_room, markdown):
        """Replies to our caller.

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
            # The user did not specify a command to get help on. Return the "Help-all" command.
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
        """
        Usage: `help-all`

        Returns a list of all commands
        """
        command_list = []

        for command in self.commands:
            command_list.append(command)

        sorted_commands = sorted(command_list)

        output = ("Type `help [command]` for more specific help about any of these commands:\n - "
                  + "\n - ".join(sorted_commands))

        return output

class Command:
    """Represents a command that can be executed by a SparkBot

    :param function: The function that this command will execute. Must return a str.
    """

    def __init__(self, function):
        self.function = function
    
    @classmethod
    def create_callback(self, respond, room_id):
        """ Creates a callback method.

        Adds the room ID to the default 'respond' method from SparkBot, simplifying the 'callback'
        experience for bot developers.

        :param respond: The 'respond' method to add the room ID to

        :param room_id: The ID of the room to preset in 'respond'
        """

        callback = functools.partial(respond, room_id)
        callback.__doc__ = ("SparkBot.respond method with room_id pre-filled, call this with ",
                            "the message you would like to reply inside the called room with.")
        return callback
        

    def execute(self, **kwargs):
        "Executes this command"

        room_id = kwargs["room_id"]

        possible_parameters = {"commandline": kwargs["commandline"],
                               "event": kwargs["event"],
                               "caller": kwargs["caller"],
                               "callback": "",
                               "room_id": room_id}

        function_parameters = signature(self.function).parameters
        parameters_to_pass = {}
        for parameter, value in possible_parameters.items():
            if parameter in list(function_parameters.keys()):
                parameters_to_pass[parameter] = value

        # Only create the callback function if it's needed
        if "callback" in parameters_to_pass:
            respond = kwargs["callback"]
            parameters_to_pass["callback"] = self.create_callback(respond, room_id)

        return self.function(**parameters_to_pass)
