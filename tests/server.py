import subprocess
from json import dumps
import random
import string
import requests
from requests.exceptions import ConnectionError

class WebexAPIEmulator():
    """ Wraps an instance of the Webex API Emulator

    :param path: `py._path.local`_ containing the path to a Webex API Emulator
    (which has already had ``npm install`` run on it)

    :param port: The port which this emulator will listen on

    :tokens: dict containing the tokens to use for this server. `tokens.json format`_

    .. _py._path.local:https://py.readthedocs.io/en/latest/path.html#py._path.local.LocalPath
    .. _tokens.json format:https://github.com/webex/webex-api-emulator/blob/master/tokens.json
    """

    def _random_alpha_string(self, length):
        """ Generate a random string consisting of ``length`` random ascii letters """
        return ''.join([random.choice(string.ascii_letters) for n in range(length)])

    def __init__(self, path, port, tokens=None):

        self.url = "http://localhost:{}/".format(port)

        self.bot_token = self._random_alpha_string(32)
        self.bot_id = self._random_alpha_string(80)
        self.bot_emails = [self._random_alpha_string(6) + "@sparkbot.io"]
        self.bot_displayname = self._random_alpha_string(6)
        self.bot_nickname = self._random_alpha_string(6)
        self.bot_firstname = self._random_alpha_string(6)
        self.bot_lastname = self._random_alpha_string(6)
        self.bot_org = self._random_alpha_string(32)
        self.server_started = False

        # Tokens that are written to tokens.json in the emulator's directory
        if tokens:
            self._tokens = tokens
        else:
            self._tokens = {
                self.bot_token: {
                    "id": self.bot_id,
                    "emails": self.bot_emails,
                    "displayName": self.bot_displayname,
                    "nickName": self.bot_nickname,
                    "firstName": self.bot_firstname,
                    "lastName": self.bot_lastname,
                    "avatar": "https://cdn-images-1.medium.com/max/1000/1*wrYQF1qZ3GePyrVn-Sp0UQ.png",
                    "orgId": self.bot_org,
                    "created": "2017-07-18T00:00:00.000Z",
                    "type": "bot"
                },
                "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ": {
                    "id": "Y2lzY29zcGFyazovL3VzL1BFT1BMRS85MmIzZGQ5YS02NzVkLTRhNDEtOGM0MS0yYWJkZjg5ZjQ0ZjQ",
                    "emails": [
                        "stsfartz@cisco.com"
                    ],
                    "displayName": "Stève Sfartz",
                    "nickName": "Stève",
                    "firstName": "Stève",
                    "lastName": "Sfartz",
                    "avatar": "https://cdn-images-1.medium.com/max/1600/1*Iel5Q6qAxgBdl_IHUx3scA.jpeg",
                    "orgId": "Y2lzY29zcGFyazovL3VzL09SR0FOSVpBVElPTi8xZWI2NWZkZi05NjQzLTQxN2YtOTk3NC1hZDcyY2FlMGUxMGY",
                    "created": "2017-07-18T00:00:00.000Z",
                    "type": "person"
                },
                "01234567890123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ": {
                    "id": "Y2lzY29zcGFyazovL3VzL1BFT1BMRS85MmIzZGQ5YS02NzVkLTRhNDEtOGM0MS0yYWJkZjg5ZjQ0ZjR",
                    "emails": [
                        "postman-test@cisco.com"
                    ],
                    "displayName": "Mr. Postman",
                    "nickName": "Posty",
                    "firstName": "Post",
                    "lastName": "Man",
                    "avatar": "https://cdn-images-1.medium.com/max/1600/1*Iel5Q6qAxgBdl_IHUx3scA.jpeg",
                    "orgId": "Y2lzY29zcGFyazovL3VzL09SR0FOSVpBVElPTi8xZWI2NWZkZi05NjQzLTQxN2YtOTk3NC1hZDcyY2FlMGUxMGY",
                    "created": "2017-07-18T00:00:00.000Z",
                    "type": "person"
                }
            }

        self.path = path
        self.port = port
        tokenfile = path.join("tokens.json")
        tokenfile.write(dumps(self._tokens))

    @property
    def tokens(self):
        """ A dict containing the authorization tokens held by this server """
        return self._tokens

    def start(self):
        self.p = subprocess.Popen(["node", "server.js"],
                                  cwd=str(self.path),
                                  env={
                                      "PORT": str(self.port),
                                      "DEBUG": "emulator:*",
                                      "BOT_UNDER_TEST": self.bot_emails[0]
                                  })

        # Wait for the server to start
        while not self.server_started:
            try:
                r = requests.get(self.url)
                if not r.status_code >= 300:
                    self.server_started = True
            except ConnectionError:
                pass

    def stop(self):
        if self.p:
            self.p.terminate()
            self.server_started = False
