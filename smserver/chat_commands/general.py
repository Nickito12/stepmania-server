""" General Chat command to handle """

from smserver import models
from smserver import smutils
from smserver.chatplugin import ChatPlugin
from smserver.chathelper import with_color
from smserver import services


class ChatHelp(ChatPlugin):
    """ Display the list of all the commands """

    command = "help"
    helper = "Show help"

    def __call__(self, resource, message):
        response = []

        commands = self.server.chat_commands

        if message:
            if message not in commands or not commands[message].can(resource.connection):
                return ["Unknown command %s" % message]

            return ["/%s: %s" % (message, commands[message].helper)]

        for command, action in sorted(commands.items()):
            if not action.can(resource.connection):
                continue

            response.append("/%s: %s" % (command, action.helper))

        return response

class ChatUserListing(ChatPlugin):
    """ List the users connected """

    command = "users"
    helper = "List users"

    def __call__(self, resource, message, *, limit=20):
        response = []

        connection = resource.connection

        users = resource.session.query(models.User).filter_by(online=True)
        max_users = self.server.config.server.get("max_users")
        if connection.room:
            users = users.filter_by(room_id=connection.room_id)
            max_users = connection.room.max_users

        response.append("%s/%s players online" % (users.count(), max_users))

        for user in users.order_by("name").limit(limit):
            response.append(
                "%s (in %s)" % (
                    user.fullname_colored(connection.room_id),
                    user.enum_status.name
                )
            )
        return response

class ChatTimestamp(ChatPlugin):
    """ Add the timestamp in the chat messages """

    command = "timestamp"
    helper = "Show timestamp"

    def __call__(self, resource, message):
        #FIXME need to be store elsewhere (don't work for the moment)

        if resource.conn.chat_timestamp:
            resource.conn.chat_timestamp = False
            resource.send("Chat timestamp disabled", target=resource.token)
        else:
            resource.send("Chat timestamp enabled", target=resource.token)
            resource.conn.chat_timestamp = True

        for user in resource.active_users:
            user.chat_timestamp = resource.conn.chat_timestamp

class FriendNotifications(ChatPlugin):
    command = "friendnotif"
    helper = "Enable notifications whenever a friend gets on/off line. /friendnotif"

    def __call__(self, resource, message):

        for user in resource.active_users:
            if user.friend_notifications:
                user.friend_notifications = False
                resource.send("Friend notifications disabled", target=resource.token)
            else:
                user.friend_notifications = True
                resource.send("Friend notifications enabled", target=resource.token)

class AddFriend(ChatPlugin):
    command = "addfriend"
    helper = "Add a friend. /addfriend user"

    def __call__(self, resource, message):
        for user in resource.connection.active_users:
            if not user:
                return
            newfriend = resource.session.query(models.User).filter_by(name=message).first()
            if not newfriend:
                resource.send("Unknown user %s" % with_color(message), target=resource.token)
                return
            if newfriend.name == user.name:
                resource.send("Cant befriend yourself", target=resource.token)
                return
            relationships = resource.session.query(models.Relationship).filter( \
                ((models.Relationship.user1_id == user.id) & (models.Relationship.user2_id == newfriend.id)) |  \
                (models.Relationship.user2_id == user.id) & (models.Relationship.user1_id == newfriend.id))
            if not relationships.first():
                resource.session.add(models.Relationship(user1_id = user.id, user2_id = newfriend.id, state = 0))
                resource.send("Friend request sent to %s" % with_color(message), target=resource.token)
            else:
                relationships = relationships.all()
                if len(relationships) != 1:
                    if friendship[0].state == 2:
                        if friendship.user1_id == user.id:
                            Unignore.__call__(self, resource, message)
                            friendship = relationships[1]
                    if friendship[1].state == 2:
                        if friendship.user1_id == user.id:
                            Unignore.__call__(self, resource, message)
                            friendship = relationships[0]
                else:
                    friendship = relationships[0]
                if friendship.state == 1:
                    resource.send("%s is already friends with you" % with_color(message), target=resource.token)
                    return
                if friendship.state == 2:
                    resource.send("Cant send %s a friend request" % with_color(message), target=resource.token)
                    return
                if friendship.user1_id == user.id:
                    resource.send("Already sent a friend request to %s" % with_color(message), target=resource.token)
                    return
                friendship.state = 1
                resource.send("Accepted friend request from %s" % with_color(message), target=resource.token)
            resource.session.commit()

class RemoveFriend(ChatPlugin):
    command = "removefriend"
    helper = "Remove a friend. /removefriend user"

    def __call__(self, resource, message):
        for user in resource.connection.active_users:
            if not user:
                return
            oldfriend = resource.session.query(models.User).filter_by(name=message).first()
            if not oldfriend:
                resource.send("Unknown user %s" % with_color(message), target=resource.token)
                return
            friendship = resource.session.query(models.Relationship).filter( \
                ((models.Relationship.user1_id == user.id) & (models.Relationship.user2_id == oldfriend.id) & ((models.Relationship.state == 1) | (models.Relationship.state == 0))) | \
                ((models.Relationship.user2_id == user.id) & (models.Relationship.user1_id == oldfriend.id) & ((models.Relationship.state == 1) | (models.Relationship.state == 0))) )
            friendships = friendship.first()
            if not friendships:
                resource.send("%s is not your friend" % with_color(message), target=resource.token)
            resource.session.delete(friendships)
            resource.session.commit()
            resource.send("%s is no longer your friend" % with_color(message), target=resource.token)


class Ignore(ChatPlugin):
    command = "ignore"
    helper = "Ignore someone(Can't send friend requests or pm). /ignore user"

    def __call__(self, resource, message):
        for user in resource.connection.active_users:
            if not user:
                return
            newignore = resource.session.query(models.User).filter_by(name=message).first()
            if not newignore:
                resource.send("Unknown user %s" % with_color(message), target=resource.token)
                return
            if newignore.name == user.name:
                resource.send("Cant ignore yourself", target=resource.token)
                return
            relationships = resource.session.query(models.Relationship).filter( \
                ((models.Relationship.user1_id == user.id) & (models.Relationship.user2_id == newignore.id)) |  \
                (models.Relationship.user2_id == user.id) & (models.Relationship.user1_id == newignore.id))
            relationships = relationships.all()
            ignored = False
            for relationship in relationships:
                if relationship.state == 0 or relationship.state == 1:
                    resource.session.delete(relationship)
                    resource.send("%s is no longer your friend" % with_color(message), target=resource.token)
                elif relationship.state == 2 and relationship.user1_id == user.id:
                    resource.send("%s is already ignored" % with_color(message), target=resource.token)
                    ignored = True
            if not ignored:
                resource.session.add(models.Relationship(user1_id = user.id, user2_id = newignore.id, state = 2))
                resource.send("%s ignored" % with_color(message), target=resource.token)
            resource.session.commit()



class Unignore(ChatPlugin):
    command = "unignore"
    helper = "Stop ignoring someone. /unignore user"

    def __call__(self, resource, message):
        for user in resource.connection.active_users:
            if not user:
                return
            newignore = resource.session.query(models.User).filter_by(name=message).first()
            if not newignore:
                resource.send("Unknown user %s" % with_color(message), target=resource.token)
                return
            ignore = resource.session.query(models.Relationship).filter_by(user1_id = user.id).filter_by(user2_id = newignore.id).filter_by(state = 2).first()
            if ignore:
                resource.session.delete(ignore)
                resource.session.commit()
                resource.send("%s unignored" % with_color(message), target=resource.token)
                return
            resource.send("%s is not currently ignored. Cant unignore" % with_color(message), target=resource.token)



class Friendlist(ChatPlugin):
    command = "friendlist"
    helper = "Show friendlist"

    def __call__(self, resource, message):
        for user in resource.connection.active_users:
            if not user:
                return
            friends = resource.session.query(models.Relationship).filter_by(state = 1).filter((models.Relationship.user1_id == user.id) | models.Relationship.user2_id == user.id).all()
            friendsStr = ""
            for friend in friends:
                if friend.user1_id == user.id:
                    frienduser = resource.session.query(models.User).filter_by(id = friend.user2_id).first()
                else:
                    frienduser = resource.session.query(models.User).filter_by(id = friend.user1_id).first()
                friendsStr += frienduser.name + ", "
            if friendsStr.endswith(", "):
                friendsStr = friendsStr[:-2]
            requests = resource.session.query(models.Relationship).filter_by(user2_id = user.id).filter_by(state = 0).all()
            requestsStr = ""
            for request in requests:
                requestsStr += resource.session.query(models.User).filter_by(id=request.user1_id).first().name + ", "
            if requestsStr.endswith(", "):
                requestsStr = requestsStr[:-2]
            requestsoutgoing = resource.session.query(models.Relationship).filter_by(user1_id = user.id).filter_by(state = 0).all()
            requestsoutgoingStr = ""
            for request in requestsoutgoing:
                requestsoutgoingStr += resource.session.query(models.User).filter_by(id=request.user2_id).first().name + ", "
            if requestsoutgoingStr.endswith(", "):
                requestsoutgoingStr = requestsoutgoingStr[:-2]
            ignores = resource.session.query(models.Relationship).filter_by(user1_id = user.id).filter_by(state = 2).all()
            ignoresStr = ""
            for ignore in ignores:
                ignoresStr += resource.session.query(models.User).filter_by(id=ignore.user2_id).first().name + ", "
            if ignoresStr.endswith(", "):
                ignoresStr = ignoresStr[:-2]

            resource.send("Friends: %s" % friendsStr, target=resource.token)
            resource.send("Incoming requests: %s" % requestsStr, target=resource.token)
            resource.send("Outgoing requests: %s" % requestsoutgoingStr, target=resource.token)
            resource.send("Ignoring: %s" % ignoresStr, target=resource.token)


class PrivateMessage(ChatPlugin):
    command = "pm"
    helper = "Send a private message. /pm user message"

    def __call__(self, resource, message):
        user = models.User.from_ids(resource.conn.users, resource.session)
        user = user[0]
        #user = resource.session.query(models.User).filter_by(online = True).filter_by(last_ip = resource.conn.ip).first()
        if not user:
            return
        message = message.split(' ', 1)
        if len(message) < 2:
            resource.send("Need a text message to send", target=resource.token)
            return
        if self.sendpm(resource, user, message[0], message[1]) == False:
            if '_' in message[0]:
                self.sendpm(resource, user, message[0].replace('_',' '), message[1])

    def sendpm(self, resource, user, receptorname, message):
        receptor = resource.session.query(models.User).filter_by(online=True).filter_by(name=receptorname).first()
        if not receptor:
            resource.send("Could not find %s online" % with_color(receptorname), target=resource.token)
            return False
        if receptor.name == user.name:
            resource.send("Cant pm yourself", target=resource.token)
            return False
        ignore = resource.session.query(models.Relationship).filter( \
            (((models.Relationship.user1_id == user.id) & (models.Relationship.user2_id == receptor.id)) |  \
            ((models.Relationship.user2_id == user.id) & (models.Relationship.user1_id == receptor.id))) &  \
            (models.Relationship.state == 2)).first()
        if ignore:
            resource.send("Cant send %s a private message" %with_color(receptorname), target=resource.token)
            return False
        if not receptor:
            resource.send("Could not find %s online" % with_color(receptorname), target=resource.token)
            return False
        resource.send("To %s : %s" % (with_color(receptor.name), message), target=resource.token)
        receptor = resource.server.find_connection(receptor.id)
        #if i do what's commented both players get the message
        #resource.send("From %s : %s" % (with_color(user.name), message), receptor)
        receptor.send(smutils.smpacket.SMPacketServerNSCCM(message="From %s : %s" % (with_color(user.name), message)))
        return True

