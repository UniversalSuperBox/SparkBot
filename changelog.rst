Changelog
=========

0.3.0
-----

* Add "Fallback" command, allowing for overriding the default behavior when a
  command is not found
* Add ability to remove the help command from the bot

0.2.0
-----

* Switch from Bottle to Falcon for the API receiver
* Update run.py.example for the switch. This greatly reduces the boilerplate
  needed to set up a SparkBot.

Existing users of SparkBot should be wary of this update. Check out the changes
to run.py.example and the new Deploy documentation to learn about the needed
conversions.

0.1.0
-----

* Add option to "yield" from a command to send messages to the user. This allows
  for multiple replies with much simpler internal code than ``callback``
  provided.
* Deprecate ``callback``, to be removed in version 1.0.0
