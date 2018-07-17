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
from types import FunctionType
from logging import Logger
from inspect import signature
from os import environ
import falcon
from ciscosparkapi import CiscoSparkAPI, WebhookEvent, Room

class SparkBot:
    """ A bot for Cisco Webex Teams

    SparkBot automatically creates a webhook for itself and will delete any other webhooks on its
    bot account. To do this, it uses the ``root_url`` parameter or ``WEBHOOK_URL`` in the
    environment to know its public URL.

    SparkBot has a ``help`` command built in by default. These may be overridden using the
    :meth:`command` decorator and providing the "help" argument and a function with your desired
    behavior on calling ``help``. See :doc:`Writing Commands </writing-commands>` for more
    information on writing commands.

    :param spark_api: CiscoSparkAPI instance that this bot should use
    :type spark_api: ciscosparkapi.CiscoSparkAPI

    :param root_url: The base URL for the SparkBot webhook receiver. May also be provided as
                     ``WEBHOOK_URL`` in the environment.
    :type root_url: str

    :param logger: Logger that the bot will output to
    :type logger: logging.Logger

    :param skip_receiver_setup: Set to "all" or "webhook" to skip setting up a receiver when
                                instancing SparkBot. "all" skips creating the receiver and the
                                webhook. "webhook" creates a receiver but does not register a
                                webhook with Webex Teams.
    :type skip_receiver_setup: "all", "webhook"
    """

    def __init__(self, spark_api, root_url=None, logger=None, skip_receiver_setup=None):

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
        self.commands["help"] = self.my_help
        self.fallback_command = None

        # Message sent to user when they request a command that doesn't exist.
        self.command_not_found_message = "Command not found. Maybe try 'help'?"

        # Cache "me" to speed up commands requiring it
        self.me = self.spark_api.people.me()

        # The output of the "help all" command should only need to be determined once.
        # See self.my_help_all to learn more.
        self._help_all_string = ""

        if skip_receiver_setup == "all":
            self.receiver = None
            return
        # Put any logic that "sets up" a receiver but not a webhook after this point

        # Create my receiver
        self.receiver = receiver.create(self)

        if skip_receiver_setup == "webhook":
            self.webhook_secret = None
            return
        # Put any logic that sets up a webhook after this point

        self.webhook_secret = receiver.random_bytes(32)

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
        """ Decorator that registers a command function into a SparkBot instance.

        :param command_strings: Callable name(s) of command. When a bot user types this (these),
                                they call the decorated function. Pass a single string for a single
                                command name. Pass a list of strings to give a command multiple
                                names.
        :type command_strings: list or str


        :param fallback: False by default, not required. If True, sets this command as a
                         "fallback command", used when the user requests a command that does not
                         exist.
        :type fallback: bool

        :raises CommandSetupError: Arguments or combination of arguments was incorrect.
                                   The error description will have more details.

        :raises TypeError: Type of arguments was incorrect.

        .. note::

            When using the default receiver, commands may not be added or removed from the bot after
            the receiver starts.

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

            new_command = function

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

    def remove_help(self):
        """Removes the help command from the bot

        This will remove the help command even if it has been overridden using
        ``@SparkBot.command("help")``

        .. note::

            When using the default receiver, commands may not be added or removed from the bot after
            the receiver starts.
        """

        self.command_not_found_message = "Command not found."
        self.commands.pop("help", None)

    def execute_command(self, command_str, suppress_exceptions=True, **kwargs):
        """Runs the command given by 'command_str' if it exists with the possible arguments in ``**kwargs``.

        Execute_command will return either a str or a generator, depending on the behavior of the
        command it calls. The receiver dispatch function calling it should be prepared for either
        possibility.

        :param command_str: The 'command' that the user wants to run. Should match a command string
                            that has previously been added to the bot.
        :type command_str: str

        :param commandline: The user's complete message to the bot parsed into a list of tokens
                            by ``shlex.split()``.
        :type commandline: list

        :param event: ciscosparkapi.WebhookEvent object describing the request causing this command.
        :type event: ciscosparkapi.WebhookEvent

        :param caller: The user who sent the message we're processing.
        :type caller: ciscosparkapi.Person

        :param room_id: The ID of the room that the message we're processing was sent in.
        :type room_id: str

        :Keyword Arguments:
            Each keyword argument sent here will be used as a possible argument for commands. For
            example, the keyword argument ``commandline=`` will allow a command function (the ones
            defined with :meth:`command`) to take an argument by the name ``commandline``.
            The current list can be found at :ref:`recognized-keywords`.

            If a logger is defined, SparkBot will raise a warning if an argument is requested
            but not provided by the ``kwargs`` given to this function. This means that there is
            either a typo in the argument on the command function or :meth:`command_dispatcher` has
            failed to do its job correctly (the first is more likely).
        """

        command_to_run = None

        # Try to find command in the commands dictionary
        if command_str in self.commands:
            command_to_run = self.commands[command_str]
        elif self.fallback_command:
            command_to_run = self.fallback_command
        else:
            raise CommandNotFound('No command found', self.command_not_found_message)

        possible_parameters = kwargs
        possible_parameters["callback"] = None

        function_parameters = signature(command_to_run).parameters

        for parameter in function_parameters.keys():
            if parameter not in possible_parameters:
                if self._logger:
                    self._logger.warn(("Parameter ", parameter, " requested by function ",
                                       command_str, " but not found internally. `None` will be ",
                                       "passed to this parameter. Check the Writing Commands ",
                                       "document for a list of supported keywords."))
                    possible_parameters[parameter] = None

        parameters_to_pass = {}
        for parameter, value in possible_parameters.items():
            if parameter in list(function_parameters.keys()):
                parameters_to_pass[parameter] = value

        # Catch generic Exception so that we always reply to the user.
        try:
            usercommandresponse = command_to_run(**parameters_to_pass)
        except Exception as error:

            # Build our logging string
            if isinstance(self._logger, Logger):
                self._logger.exception(' '.join(['User caused:', type(error).__name__,
                                                error.args[0], 'with the command:', command_str]))
            try:
                errordescription = error.args[1]
            except IndexError:
                errordescription = ("Something happened internally. "
                                    "For more information, contact the bot author.")
            # Make response
            finalresponse = " ".join(["⚠️ Error:", errordescription])

        else:
            finalresponse = usercommandresponse

        return finalresponse

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
