from disco.bot.command import CommandLevels
from commands.client import TrelloClient
from disco.bot import Plugin, Config
from pymongo import MongoClient
import time

SUPPORTED_SYSTEMS = ['android', 'ios', 'windows', 'linux', 'mac']


def command_level_getter(bot, actor):
    return CommandLevels.TRUSTED


class BaseConfig(Config):
    trello_key = "c3194bfe3a5e7644b996ba48542e0b00"
    trello_token = "6ca84163ff8450f075011feb3a528d7f6d6d9c1a0054da8b8c2908d1971c3650"


class BasePlugin(Plugin):
    _shallow = True

    def __init__(self, bot, config):
        super(BasePlugin, self).__init__(bot, config)

        self.client = MongoClient(
            self.config.mongodb_host,
            self.config.mongodb_port,
            username=self.config.mongodb_username,
            password=self.config.mongodb_password
        )

        self.trello_client = TrelloClient(
            self.config.trello_key,
            self.config.trello_token
        )

        self.users = self.client.experience.users
        self.actions = self.client.experience.actions
        self.messages = self.client.reactions.messages

    def shared_add_xp(self, user_id, amount):
        uid = str(user_id)
        user = self.users.find_one({'user_id': uid})
        if user is None:
            user = {'user_id': uid, 'xp': 0}
            self.users.insert_one(user)
        total = user['xp'] + amount
        self.users.update_one({'user_id': uid}, {'$set': {'xp': total}})

    def shared_get_actions(self, user_id, type):
        return self.actions.find({"user_id": str(user_id), "type": type})

    def shared_get_user(self, id):
        """
        Get a user by their ID
        :param id: the user's ID
        :return: a dictionary containing the user's information
        """
        result = self.users.find_one({
            "user_id": str(id)
        })

        if result is None:
            insert_result = self.users.insert_one({
                "user_id": str(id),
                "xp": 0
            })
            return self.users.find_one({"_id": insert_result.inserted_id})

        return result

    def shared_handle_action(self, user_id, action, has_time_limit):
        """ handles giving user XP for an action they did. """
        actions = []
        for previous_action in self.shared_get_actions(user_id, action):
            # if action happened less than 24 hours ago, add it.
            if previous_action.get("time", 0) + 86400.0 >= time.time():
                actions.append(previous_action)
        if len(actions) >= self.config.reward_limits[action]:
            return
        self.send_to_me()
        user = self.shared_get_user(user_id)
        self.users.update_one({
            "user_id": str(user_id)
        }, {
            "$set": {
                "xp": user["xp"] + self.config.rewards[action]
            }
        })
        if has_time_limit:
            self.send_to_me()
            self.actions.insert_one({
                "user_id": str(user_id),
                "type": action,
                "time": time.time()
            })
