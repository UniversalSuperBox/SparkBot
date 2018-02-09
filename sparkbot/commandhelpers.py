""" Helpful additional functionality for commands to take advantage of """

from re import match
from ciscosparkapi import CiscoSparkAPI, Room, Person, SparkApiError

def is_group(api, room):
    """Determines if the specified room is a group (multiple people) or direct (one-on-one)

    :param api: CiscoSparkAPI instance to query Spark with.

    :param room: The room to check the status of. May be a CiscoSparkAPI Room or a
                 Spark room ID as a string.

    :returns: True if the room is a group, False if it is not.
    """
    if isinstance(room, Room):
        check_room = room
    elif isinstance(room, str):
        check_room = api.rooms.get(room)
    else:
        raise TypeError("room must be of type str or CiscoSparkAPI.Room")

    return check_room.type == 'group'

def mention_person(person):
    """ Creates a "mention" for the specified person.

    :param person: The person to mention (must be CiscoSparkAPI.Person)

    :returns: String with the format "<@personId:[personId]|[firstName]>"
    """

    mention = ''.join(["<@personId:", person.id, "|", person.firstName, ">"])
    return mention

def check_if_in_org(organization, person):
    """ Ensures that the given person is inside the desired organization

    :param api: CiscoSparkAPI instance to query Spark with.

    :param organization: The ID of the organization to find this user in

    :param person: The person to check against the organization. Must be CiscoSparkAPI.Person.
    """

    if not organization or not isinstance(organization, str):
        raise TypeError("organization must be of type str")

    if not isinstance(person, Person):
        raise TypeError("person must be of type CiscoSparkAPI.Person")

    if person.orgId == organization:
        return True
    else:
        return False

def get_person_by_email(api, person_email):
    """ Gets a person by e-mail

    :param api: CiscoSparkAPI instance to query Spark with.

    :param person_email: The e-mail address of the person to search for.

    :returns: ciscosparkapi.Person of found person

    :raises: ValueError if person_email is invalid or does not return exactly one person

    :raises: TypeError if argument types are incorrect
    """

    # Check arguments
    email_regex = r"[^@]+@[^@]+\.[^@]+"
    if not person_email and isinstance(person_email, str):
        raise TypeError("person_email must be of type str")
    elif not match(email_regex, person_email):
        raise ValueError("Incorrect e-mail format")

    people = list(api.list(email=person_email))
    number_of_people = len(people)

    if number_of_people == 1:
        person = people[0]
    elif number_of_people > 1:
        raise ValueError("More than one user found for e-mail")
    elif number_of_people < 1:
        raise ValueError("No person found for e-mail")

    return person

def get_person_by_spark_id(api, person_id):
    """ Gets a person by their Spark ID

    :param api: CiscoSparkAPI instance to query Spark with.

    :param person_id: The person's unique ID from Spark

    :returns: ciscosparkapi.Person of found person
    """

    if person_id and isinstance(person_id, str):
        # Get this user by ID
        try:
            person = api.get(person_id)
        except SparkApiError:
            raise ValueError("No person found for ID")
    else:
        raise ValueError("No person found for ID")

    return person

def check_if_in_team(api, team_id, person):
    """ Checks if a person is in a given team

    :param api: CiscoSparkAPI instance to query Spark with.

    :param team_id: The ID of the team to check for

    :param person: The person to check against the team
    """
    team_memberships = api.team_memberships.list(team_id)

    # Check every membership to see if this person is contained within
    for membership in team_memberships:
        if person.id == membership.personId:
            return True

    return False

def minargs(numargs, commandline):
    """ Ensures that you have more than [numargs] arguments in [commandline] """

    commandlineargs = (len(commandline) - 1)

    return numargs <= commandlineargs
