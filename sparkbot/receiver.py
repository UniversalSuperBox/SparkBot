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
from bottle import request, post, get, HTTPResponse, run, abort
from ciscosparkapi import CiscoSparkAPI, Webhook

BOT_INSTANCE = None
SPARK_API = None
WEBHOOK_KEY = None
ME = None

@post('/sparkreceiver')
def call_core():
    """Receives messages and passes them to the sparkbot instance in BOT_INSTANCE"""

    global ME

    if not BOT_INSTANCE or not SPARK_API:
        return HTTPResponse(status=500)

    if not request.json:
        return HTTPResponse(status=400, body="Missing command")

    json_data = request.json

    if WEBHOOK_KEY:
        
        try:
            # Get the HMAC of the incoming message
            expected_digest = request.headers["x-spark-signature"]
        except KeyError:
            # We expected but didn't receive a signature. Don't process any further.
            return HTTPResponse(status=403)

        real_digest = hmac.new(WEBHOOK_KEY, msg=request.body.read(), digestmod=hashlib.sha1)
        if not real_digest.hexdigest() == expected_digest:
            # The received signature doesn't match the one we expect.
            return HTTPResponse(status=403)

    # Loop prevention
    if not ME:
        # Cache ME since the Spark API can be really slow
        ME = SPARK_API.people.me()
    message_person_id = json_data["actorId"]
    if message_person_id == ME.id:
        # Message was sent by me (bot); do not respond.
        return HTTPResponse(status=204)

    bot_thread = Thread(target=BOT_INSTANCE.commandworker, args=(json_data,))
    bot_thread.start()

    return HTTPResponse(status=204)
