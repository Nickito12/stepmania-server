""" General Chat command to handle """

from smserver import models
from smserver.chatplugin import ChatPlugin


class ChatHelp(ChatPlugin):
    command = "help"
    helper = "Show help"

    def __call__(self, serv, message):
        for command, action in sorted(serv.server.chat_commands.items()):
            if not action.can(serv):
                continue

            serv.send_message("/%s: %s" % (command, action.helper), to="me")

class ChatUserListing(ChatPlugin):
    command = "users"
    helper = "List users"

    def __call__(self, serv, message):
        users = serv.session.query(models.User).filter_by(online=True)
        max_users = serv.server.config.server.get("max_users")
        if serv.room:
            users = users.filter_by(room_id=serv.room.id)
            max_users = serv.room.max_users

        users = users.all()
        serv.send_message("%s/%s players online" % (len(users), max_users), to="me")

        for user in users:
            serv.send_message(
                "%s (in %s)" % (
                    user.fullname_colored(serv.conn.room),
                    user.enum_status.name),
                to="me")


class ChatTimestamp(ChatPlugin):
    command = "timestamp"
    helper = "Show timestamp"

    def __call__(self, serv, message):
        if serv.conn.chat_timestamp:
            serv.conn.chat_timestamp = False
            serv.send_message("Chat timestamp disabled", to="me")
        else:
            serv.send_message("Chat timestamp enabled", to="me")
            serv.conn.chat_timestamp = True

        for user in serv.active_users:
            user.chat_timestamp = serv.conn.chat_timestamp
