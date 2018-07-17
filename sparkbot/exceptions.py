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

"""Exceptions thrown by SparkBot"""

class SparkBotError(Exception):
    """Generic exception"""

class CommandNotFound(SparkBotError):
    """Raised when a command is not found for the given request"""

class CommandSetupError(SparkBotError):
    """Raised when it is impossible to add the specified command for some reason.

    For example, this is raised when:

    * Attempting to add more than one fallback command
    * Attempting to add a non-fallback command with no command strings
    """
