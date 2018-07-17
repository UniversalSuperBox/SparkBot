import pytest
import subprocess
import server
from random import SystemRandom
import string
from unittest import mock
from multiprocessing import Process
from time import sleep
from sparkbot import SparkBot, receiver
from sparkbot.exceptions import CommandSetupError
from wsgiref import simple_server
import requests
from ast import literal_eval
from requests.exceptions import ConnectionError
from ciscosparkapi import CiscoSparkAPI
import falcon

class TestAPI:

    def random_bytes(self, length):
        """Returns a random bytes array with uppercase and lowercase letters, of length length"""
        cryptogen = SystemRandom()
        my_random_string = ''.join([cryptogen.choice(string.ascii_letters) for _ in range(length)])
        my_random_bytes = my_random_string.encode(encoding='utf_8')

        return my_random_bytes

    @pytest.fixture(scope="session")
    def emulator_prereqs(self):
        """ Ensures that the WebEx API emulator can be run """

        # Make sure we can start node
        try:
            subprocess.run("node -v", shell=True, check=True)
        except subprocess.CalledProcessError:
            pytest.fail("Unable to execute Node. I won't be able to test the bot. Please install node.js and try again.")

        return True

    @pytest.fixture(scope="session")
    def emulator_server_zip(self, tmpdir_factory, emulator_prereqs):
        """ Returns a zipfile.ZipFile containing an installed emulator server """

        from subprocess import CalledProcessError
        import zipfile
        import shutil
        from urllib.request import urlretrieve
        import os

        tmpdir = tmpdir_factory.mktemp("emulator")

        fresh_emulator_zip = ".testcache/webex-api-emulator-fresh.zip"
        fresh_emulator_zip_extract_dir = tmpdir.join("webex-api-emulator")
        installed_emulator_zip_filename = ".testcache/webex-api-emulator-installed"

        try:
            os.mkdir(".testcache")
        except FileExistsError:
            pass

        urlretrieve("https://github.com/webex/webex-api-emulator/archive/master.zip", fresh_emulator_zip)

        with zipfile.ZipFile(fresh_emulator_zip) as myzip:
            first_member = myzip.namelist()[0]
            myzip.extractall(path=str(fresh_emulator_zip_extract_dir))

        built_server_directory = fresh_emulator_zip_extract_dir.join(first_member)

        print("Building zip")
        try:
            subprocess.run(["npm install"], shell=True, check=True, cwd=str(built_server_directory))
        except CalledProcessError:
            pytest.fail("Failed to run `npm install`. Try again in a few seconds, then try deleting the '.testcache' folder.")

        # Pack the installed files into a new zip
        installed_emulator_zip = shutil.make_archive(installed_emulator_zip_filename,
                                                     "zip",
                                                     str(built_server_directory))

        newzip_read = zipfile.ZipFile(installed_emulator_zip)
        yield newzip_read
        newzip_read.close()

    @pytest.fixture
    def emulator_server_files(self, tmpdir, emulator_server_zip):
        """ Returns a path to a WebEx API emulator in temporary storage as a `py._path.local`_

        .. _py._path.local:https://py.readthedocs.io/en/latest/path.html#py._path.local.LocalPath
        """

        emulator_server_zip.extractall(path=str(tmpdir))

        # Python 3.6+ had a behavior change for zip files. Zipfiles created on
        # 3.5 have `webex-api-emulator-master` as their first component. 3.6+
        # zipfiles do not have this.

        zip_component = ""

        if emulator_server_zip.namelist()[0] == "webex-api-emulator-master/":
            zip_component = "webex-api-emulator-master/"

        return tmpdir.join(zip_component)

    @pytest.fixture(scope="session")
    def unique_port(self):
        """ Returns a generator that counts up, used for port numbers for the emulator server.

        To use this counter, use 'unique_port.__next()'
        """

        from itertools import count

        return count(start=10001)

    @pytest.fixture
    def emulator_server(self, emulator_server_files, unique_port):
        """ Starts up and returns a WebEx API emulator as a server.WebexAPIEmulator """

        port = unique_port.__next__()

        emulator = server.WebexAPIEmulator(emulator_server_files, port)

        emulator.start()
        yield emulator
        emulator.stop()

    def get_spark_api(self, server):
        """
        Returns a ciscosparkapi.CiscoSparkAPI object for the server.WebexAPIEmulator
        specified by 'server'
        """
        return CiscoSparkAPI(base_url=server.url, access_token=server.bot_token)

    @pytest.fixture
    def full_bot_setup(self, emulator_server, unique_port):
        """ Sets up everything needed to test a bot, including a set-up webhook and receiver

        To use this fixture, first run ``full_bot_setup["receiver_process"].start()`` to run the
        receiver AFTER you have added commands to the bot. Next, ``GET receiver_webhook_url`` to
        prevent a race condition between the server startup and your test.  Then, use
        ``self.invoke_bot()`` or your preferred method to get a response from the bot.

        :returns: Dict with the format
                    {
                        "bot": sparkbot.SparkBot,
                        "receiver": sparkbot.receiver,
                        "bot_api": ciscosparkapi.CiscoSparkAPI,
                        "aux_api": ciscosparkapi.CiscoSparkAPI,
                        "emulator": server.WebexAPIEmulator,
                        "receiver_process": subprocessing.Process,
                        "receiver_webhook_url": str
                    }
                  ``aux_api`` is a second Spark API set up for the given emulator.
        """
        from logging import getLogger

        return_items = {}

        return_items["bot_api"] = self.get_spark_api(emulator_server)
        receiver_port = unique_port.__next__()
        return_items["receiver_webhook_url"] = "http://127.0.0.1:" + str(receiver_port)
        return_items["aux_api"] = CiscoSparkAPI(base_url=emulator_server.url,
                                                access_token="0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        return_items["bot"] = SparkBot(return_items["bot_api"],
                                       root_url = return_items["receiver_webhook_url"],
                                       logger = getLogger(name="Bot"))
        secret = self.random_bytes(32)
        return_items["receiver"] = receiver.create(return_items["bot"])
        return_items["emulator"] = emulator_server
        return_items["bot_api"].webhooks.create("myBot",
                                                return_items["receiver_webhook_url"],
                                                "messages",
                                                "created",
                                                secret=secret.decode())

        receiver_server = simple_server.make_server("localhost",
                                                    receiver_port,
                                                    return_items["receiver"])

        receiver_process = Process(target=receiver_server.serve_forever)
        return_items["receiver_process"] = receiver_process

        yield return_items

        receiver_process.terminate()
        receiver_process.join()

    def start_receiver(self, receiver_process, url):
        """ Starts the receiver held by receiver_process and waits for it to come up.

        receiver_process should be a multiprocessing.Process, its target should be receiver.run().

        url is the receiver URL that this method will expect to be able to reach when the receiver
        is up.
        """

        # It would be simpler to start the server in the full_bot_setup fixture, but that isn't
        # possible due to the way that Python multiprocessing works. Specifically, trying to add
        # new commands to the bot after starting a receiver will always fail since the process
        # "holds" the old version of the bot.

        receiver_process.start()

        while True:
            try:
                r = requests.get(url)
                print(r.status_code)
                break
            except ConnectionError:
                pass

    def invoke_bot(self, spark_api, bot_id, bot_displayname, markdown, room_name="Test", expected_replies=1, timeout=10):
        """ Creates a new room, adds the bot, and messages the bot using the markdown specified.

        :param spark_api: ciscosparkapi.CiscoSparkAPI of another user (not the bot we're testing)

        :param bot_id: ID of the bot that we are invoking

        :param bot_displayname: Display name of the bot that we are invoking

        :param markdown: markdown-formatted message to send to the bot

        :param room_name: The name of the room to create. Must be provided unique within each test.
                          Failure to provide a unique name will cause unexpected results.

        :param expected_replies: The number of replies to wait for from the bot

        :param timeout: Maximum number of seconds to wait for the bot to respond.

        :returns: Response from bot as a ciscosparkapi.Message if ``expected_replies`` is 1,
                  list of responses from bot if it is greater than 1.
        """

        message = "<@personId:{}|{}> ".format(bot_id, bot_displayname) + markdown
        room = spark_api.rooms.create(room_name)
        spark_api.memberships.create(roomId=room.id, personId=bot_id)
        spark_api.messages.create(roomId=room.id, markdown=message)

        sleep(1)

        bot_replies = []

        # Timeout*2 because we're sleeping for 0.5 seconds and incrementing i by 1 each time
        for i in range(0, timeout*2):

            # Pull each message from the test room. If we match one that's already in bot_replies,
            # go on to the next one. Otherwise, if the reply came from the bot, store it.
            for message in spark_api.messages.list(room.id):
                if message.personId == bot_id and not message.id in [stored_message.id for stored_message in bot_replies]:
                    bot_replies.append(message)
                    next

            if len(bot_replies) == expected_replies or i >= timeout:
                break
            else:
                sleep(0.5)

        # Order the replies by their send time
        bot_replies.sort(key=lambda r: r.created)

        if expected_replies == 1:
            return bot_replies[0]
        else:
            return bot_replies

    def test_server_sanity(self, emulator_server):
        """Ensures the API server is sane"""

        spark_api = self.get_spark_api(emulator_server)

        me = spark_api.people.me()

        assert me.displayName == emulator_server.bot_displayname
        assert me.lastName == emulator_server.bot_lastname
        assert me.firstName == emulator_server.bot_firstname
        assert me.orgId == emulator_server.bot_org
        assert me.nickName == emulator_server.bot_nickname
        assert me.emails == emulator_server.bot_emails
        assert me.id == emulator_server.bot_id

    def test_add_command(self, emulator_server):
        """Tests use of the @SparkBot.command() decorator to add a command to the bot"""

        spark_api = self.get_spark_api(emulator_server)

        bot = SparkBot(spark_api)

        @bot.command("ping")
        def ping():
            return 'pong'

        assert bot.execute_command("ping") == "pong"

    def test_callback(self, emulator_server):
        """Tests the bot's ability to give a callback function"""

        spark_api = self.get_spark_api(emulator_server)
        bot = SparkBot(spark_api)
        room_id = "ASDF1234"

        temp_send_message = mock.MagicMock()
        bot.send_message = temp_send_message

        @bot.command("callback")
        def callingback(callback):
            callback("Some markdown")

        bot.execute_command("callback", room_id=room_id)

        assert temp_send_message.called_with(room_id, "Some markdown")

    def test_arg_passing(self, emulator_server):
        """Tests that arguments are passed to commands as expected"""

        spark_api = self.get_spark_api(emulator_server)
        bot = SparkBot(spark_api)

        temp_commandline = mock.MagicMock()
        temp_event = mock.MagicMock()
        temp_caller = mock.MagicMock()
        temp_room_id = mock.MagicMock()

        @bot.command("arguments")
        def arguments(commandline, event, caller, room_id):
            return (commandline, event, caller, room_id)

        execution = bot.execute_command("arguments", commandline=temp_commandline,
                                        event=temp_event,
                                        caller=temp_caller,
                                        room_id=temp_room_id)

        assert execution == (temp_commandline, temp_event, temp_caller, temp_room_id)

    def test_skip_receiver_all(self, emulator_server):
        """Tests that it is possible to skip "all" to prevent receiver setup """

        spark_api = self.get_spark_api(emulator_server)
        spark_api.webhooks = mock.MagicMock()
        bot = SparkBot(spark_api, skip_receiver_setup="all")

        assert bot.receiver == None
        assert not spark_api.webhooks.list.called

    def test_skip_receiver_webhook(self, emulator_server):
        """Tests that it is possible to skip "webhook" to prevent webhook setup """

        spark_api = self.get_spark_api(emulator_server)
        spark_api.webhooks = mock.MagicMock()
        bot = SparkBot(spark_api, skip_receiver_setup="webhook")

        assert isinstance(bot.receiver, falcon.API)
        assert not spark_api.webhooks.list.called

    def test_full_arg_passing(self, full_bot_setup):
        """Tests that arguments are passed to commands as expected (now with the emulator).

        This ensures that the command_dispatcher is working correctly.
        """

        bot = full_bot_setup["bot"]
        aux_api = full_bot_setup["aux_api"]
        emulator = full_bot_setup["emulator"]

        @bot.command("arguments")
        def arguments(commandline, event, caller, room_id):
            return (str({"commandline": commandline,
                    "eventEmail": event.data.personEmail,
                    "callerEmail": caller.emails[0],
                    "eventRoom": event.data.roomId,
                    "argRoom": room_id}))

        self.start_receiver(full_bot_setup["receiver_process"], full_bot_setup["receiver_webhook_url"])

        bot_reply = self.invoke_bot(full_bot_setup["aux_api"],
                                    emulator.bot_id,
                                    emulator.bot_displayname,
                                    "arguments")

        reply_contents_dict = literal_eval(bot_reply.text)

        # Only the ['arguments'] needs to be literal. The event and caller have their
        # email in common. The event's room and the 'room_id' argument should also be the same
        assert reply_contents_dict["commandline"] == ['arguments']
        assert reply_contents_dict["eventEmail"] == reply_contents_dict["callerEmail"]
        assert reply_contents_dict["eventRoom"] == reply_contents_dict["argRoom"]

    def test_full_nocommand(self, full_bot_setup):
        """Tests the bot's error handling when an incorrect command is given"""

        bot = full_bot_setup["bot"]
        aux_api = full_bot_setup["aux_api"]
        emulator = full_bot_setup["emulator"]

        self.start_receiver(full_bot_setup["receiver_process"], full_bot_setup["receiver_webhook_url"])

        bot_reply = self.invoke_bot(full_bot_setup["aux_api"],
                                    emulator.bot_id,
                                    emulator.bot_displayname,
                                    "ping")

        assert "Command not found" in bot_reply.text

    def test_full_ping(self, full_bot_setup):
        """Tests a ping command through the emulator"""

        bot = full_bot_setup["bot"]
        emulator = full_bot_setup["emulator"]

        @bot.command("ping")
        def ping():
            return "pong"

        self.start_receiver(full_bot_setup["receiver_process"], full_bot_setup["receiver_webhook_url"])

        bot_reply = self.invoke_bot(full_bot_setup["aux_api"],
                                    emulator.bot_id,
                                    emulator.bot_displayname,
                                    "ping")

        assert "pong" in bot_reply.text

    def test_full_bad_formatting(self, full_bot_setup):
        """Tests that an incorrectly formatted command returns an error safely"""

        emulator = full_bot_setup["emulator"]

        self.start_receiver(full_bot_setup["receiver_process"], full_bot_setup["receiver_webhook_url"])

        # Wait for server to come up
        requests.get(full_bot_setup["receiver_webhook_url"])

        bot_reply = self.invoke_bot(full_bot_setup["aux_api"],
                                    emulator.bot_id,
                                    emulator.bot_displayname,
                                    "Command 'without completed quotes")

        assert "format" in bot_reply.text

    def test_command_strings_list(self, full_bot_setup):
        """Tests that a command can be called by multiple names"""

        bot = full_bot_setup["bot"]
        aux_api = full_bot_setup["aux_api"]
        emulator = full_bot_setup["emulator"]

        @bot.command(["ping", "ding"])
        def ping():
            return "pong"

        self.start_receiver(full_bot_setup["receiver_process"], full_bot_setup["receiver_webhook_url"])

        bot_reply_1 = self.invoke_bot(aux_api,
                        emulator.bot_id,
                        emulator.bot_displayname,
                        "ping",
                        room_name="test1")

        bot_reply_2 = self.invoke_bot(aux_api,
                        emulator.bot_id,
                        emulator.bot_displayname,
                        "ding",
                        room_name="test2")

        assert "pong" in bot_reply_1.text and "pong" in bot_reply_2.text

    def test_full_help(self, full_bot_setup):
        """Tests the default help-all command (and the default help command's ability to call it)"""

        aux_api = full_bot_setup["aux_api"]
        emulator = full_bot_setup["emulator"]

        self.start_receiver(full_bot_setup["receiver_process"], full_bot_setup["receiver_webhook_url"])

        bot_reply_1 = self.invoke_bot(aux_api,
                        emulator.bot_id,
                        emulator.bot_displayname,
                        "help",
                        room_name="test1")

        bot_reply_2 = self.invoke_bot(aux_api,
                        emulator.bot_id,
                        emulator.bot_displayname,
                        "help all",
                        room_name="test3")

        assert bot_reply_1.markdown == (
"""Type `help [command]` for more specific help about any of these commands:
 - help"""
        )

        assert bot_reply_1.markdown == bot_reply_2.markdown

    def test_full_internal_error_text(self, full_bot_setup):
        """Tests that unhandled exceptions in commands with error text are handled safely"""

        bot = full_bot_setup["bot"]
        aux_api = full_bot_setup["aux_api"]
        emulator = full_bot_setup["emulator"]

        @bot.command("exception")
        def cause_exception():
            raise ValueError("Whoops", "Hey, an exception")

        self.start_receiver(full_bot_setup["receiver_process"], full_bot_setup["receiver_webhook_url"])

        bot_reply = self.invoke_bot(aux_api, emulator.bot_id, emulator.bot_displayname, "exception", room_name="test1")

        assert bot_reply.text == "⚠️ Error: Hey, an exception"

    def test_full_internal_error(self, full_bot_setup):
        """Tests that unhandled exceptions in commands without error text are handled safely"""

        bot = full_bot_setup["bot"]
        aux_api = full_bot_setup["aux_api"]
        emulator = full_bot_setup["emulator"]

        @bot.command("exception")
        def cause_exception():
            raise ValueError("Whoops")

        self.start_receiver(full_bot_setup["receiver_process"], full_bot_setup["receiver_webhook_url"])

        bot_reply = self.invoke_bot(aux_api, emulator.bot_id, emulator.bot_displayname, "exception", room_name="test1")

        assert bot_reply.text == "⚠️ Error: Something happened internally. For more information, contact the bot author."

    def test_full_yield_results(self, full_bot_setup):
        """Tests that ``yield``ing from a function causes multiple replies"""

        bot = full_bot_setup["bot"]
        aux_api = full_bot_setup["aux_api"]
        emulator = full_bot_setup["emulator"]

        @bot.command("two-replies")
        def two_replies(callback):
            yield "Reply 1!"
            yield "Reply 2!"

        self.start_receiver(full_bot_setup["receiver_process"], full_bot_setup["receiver_webhook_url"])

        bot_replies = self.invoke_bot(aux_api, emulator.bot_id, emulator.bot_displayname, "two-replies", expected_replies=2, room_name="test1")

        assert bot_replies[0].text == "Reply 1!"
        assert bot_replies[1].text == "Reply 2!"

    def test_full_fallback(self, full_bot_setup):
        """Tests fallback commands"""

        bot = full_bot_setup["bot"]
        aux_api = full_bot_setup["aux_api"]
        emulator = full_bot_setup["emulator"]

        @bot.command(fallback=True)
        def fallback():
            return "This is the fallback command"

        self.start_receiver(full_bot_setup["receiver_process"], full_bot_setup["receiver_webhook_url"])

        bot_reply = self.invoke_bot(aux_api, emulator.bot_id, emulator.bot_displayname, "exception", room_name="test1")

        assert bot_reply.text == "This is the fallback command"

    def test_full_remove_help(self, full_bot_setup):
        """Tests that the Help command can be removed from the bot"""

        bot = full_bot_setup["bot"]
        aux_api = full_bot_setup["aux_api"]
        emulator = full_bot_setup["emulator"]

        bot.remove_help()

        self.start_receiver(full_bot_setup["receiver_process"], full_bot_setup["receiver_webhook_url"])

        bot_reply = self.invoke_bot(aux_api, emulator.bot_id, emulator.bot_displayname, "help", room_name="test1")

        assert bot_reply.text == "⚠️ Error: Command not found."

    def test_help_multiple_command_names(self, emulator_server):
        """Tests the default help command's ability to group commands"""

        # Since we've already tested help and help_all with the full setup, we
        # only need to call the function on the bot directly.

        spark_api = self.get_spark_api(emulator_server)
        bot = SparkBot(spark_api)

        @bot.command(["name1", "name2"])
        def multiple_names():
            pass

        @bot.command("z")
        def z_command():
            pass

        bot_reply = bot.my_help_all()

        assert bot_reply == (
"""Type `help [command]` for more specific help about any of these commands:
 - help
 - name1, name2
 - z"""
        )

    def test_fallback_failure_on_multiple(self, emulator_server):
        """Tests that trying to set more than one fallback command fails"""

        spark_api = self.get_spark_api(emulator_server)
        bot = SparkBot(spark_api)

        @bot.command(fallback=True)
        def fallback():
            return "This is the fallback command"

        with pytest.raises(CommandSetupError):
            @bot.command(fallback=True)
            def second_fallback():
                return "This isn't going to work."

    def test_receiver_incorrect_hmac(self, emulator_server, unique_port):
        """Tests that the receiver will reject a message with an incorrect signature"""

        spark_api = self.get_spark_api(emulator_server)
        bot = SparkBot(spark_api)
        receiver_port = unique_port.__next__()
        webhook_url = ''.join(["http://127.0.0.1:", str(receiver_port), "/sparkbot"])

        # Give the receiver an incorrect key
        bot.webhook_secret = b"1234"
        my_receiver = receiver.create(bot)

        # Now, start the receiver in another process...
        receiver_server = simple_server.make_server("localhost",
                                                    receiver_port,
                                                    my_receiver)

        receiver_process = Process(target=receiver_server.serve_forever)

        self.start_receiver(receiver_process, webhook_url)

        try:
            # Send a good request to the server with a junk signature.
            payload = {
                "id": "Y2lzY29zcGFyazovL3VzL1dFQkhPT0svZjRlNjA1NjAtNjYwMi00ZmIwLWEyNWEtOTQ5ODgxNjA5NDk3",
                "name": "New message in 'Project Unicorn' room",
                "resource": "messages",
                "event": "created",
                "filter": "roomId=Y2lzY29zcGFyazovL3VzL1JPT00vYmJjZWIxYWQtNDNmMS0zYjU4LTkxNDctZjE0YmIwYzRkMTU0",
                "orgId": "OTZhYmMyYWEtM2RjYy0xMWU1LWExNTItZmUzNDgxOWNkYzlh",
                "createdBy": "Y2lzY29zcGFyazovL3VzL1BFT1BMRS9mNWIzNjE4Ny1jOGRkLTQ3MjctOGIyZi1mOWM0NDdmMjkwNDY",
                "appId": "Y2lzY29zcGFyazovL3VzL0FQUExJQ0FUSU9OL0MyNzljYjMwYzAyOTE4MGJiNGJkYWViYjA2MWI3OTY1Y2RhMzliNjAyOTdjODUwM2YyNjZhYmY2NmM5OTllYzFm",
                "ownedBy": "creator",
                "status": "active",
                "actorId": "Y2lzY29zcGFyazovL3VzL1BFT1BMRS9mNWIzNjE4Ny1jOGRkLTQ3MjctOGIyZi1mOWM0NDdmMjkwNDY",
                "data":{
                    "id": "Y2lzY29zcGFyazovL3VzL01FU1NBR0UvOTJkYjNiZTAtNDNiZC0xMWU2LThhZTktZGQ1YjNkZmM1NjVk",
                    "roomId": "Y2lzY29zcGFyazovL3VzL1JPT00vYmJjZWIxYWQtNDNmMS0zYjU4LTkxNDctZjE0YmIwYzRkMTU0",
                    "personId": "Y2lzY29zcGFyazovL3VzL1BFT1BMRS9mNWIzNjE4Ny1jOGRkLTQ3MjctOGIyZi1mOWM0NDdmMjkwNDY",
                    "personEmail": "matt@example.com",
                    "created": "2015-10-18T14:26:16.000Z"
                }
            }
            r = requests.post(webhook_url, json=payload, headers={"x-spark-signature":"asdf1234"})

        finally:
            receiver_process.terminate()
            receiver_process.join()

        assert r.status_code == 403

    def test_receiver_junk_data(self, emulator_server, unique_port):
        """Tests that the receiver will reject an incorrectly crafted message"""

        spark_api = self.get_spark_api(emulator_server)
        bot = SparkBot(spark_api)
        receiver_port = unique_port.__next__()
        webhook_url = ''.join(["http://127.0.0.1:", str(receiver_port) + "/sparkbot"])

        # Give the receiver an incorrect key
        bot.webhook_secret = b"1234"
        my_receiver = receiver.create(bot)

        # Now, start the receiver in another process...
        receiver_server = simple_server.make_server("localhost",
                                                    receiver_port,
                                                    my_receiver)

        receiver_process = Process(target=receiver_server.serve_forever)

        self.start_receiver(receiver_process, webhook_url)

        try:
            # Send nothing.
            r = requests.post(webhook_url)
        finally:
            receiver_process.terminate()
            receiver_process.join()

        assert r.status_code == 400

    def test_incorrect_init(self, emulator_server):
        """Tests that the bot will fail to run when given incorrect arguments"""

        spark_api = self.get_spark_api(emulator_server)

        with pytest.raises(TypeError):
            SparkBot("This is not a CiscoSparkAPI")

        with pytest.raises(TypeError):
            SparkBot(spark_api, logger="This is not a logger")

    def test_bad_command_strings(self, emulator_server):
        """Tests that the bot will fail to add a command with the incorrect argument"""

        spark_api = self.get_spark_api(emulator_server)
        bot = SparkBot(spark_api)

        with pytest.raises(CommandSetupError):
            @bot.command("")
            def ping():
                return "pong"

    def test_bad_decorator_call(self, emulator_server):
        """Tests that the bot will fail to add a command when command() is called with no arguments"""

        spark_api = self.get_spark_api(emulator_server)
        bot = SparkBot(spark_api)

        with pytest.raises(CommandSetupError):
            @bot.command
            def ping():
                return "pong"

    def test_bad_decorator_type(self, emulator_server):
        """Tests that the bot will fail to add a command with the incorrect argument type"""

        spark_api = self.get_spark_api(emulator_server)
        bot = SparkBot(spark_api)

        with pytest.raises(TypeError):
            @bot.command(bot)
            def ping(bot):
                return "pong"

    def test_bad_decorator_embedded_type(self, emulator_server):
        """Tests that the bot will fail to add a command with the incorrect argument type"""

        spark_api = self.get_spark_api(emulator_server)
        bot = SparkBot(spark_api)

        with pytest.raises(TypeError):
            @bot.command([bot, "stuff"])
            def ping():
                return "pong"
