from disco.bot.command import CommandLevels
from disco.bot import Plugin
from pymongo import MongoClient

SUPPORTED_SYSTEMS = ['android', 'ios', 'windows', 'linux', 'mac']


def command_level_getter(bot, actor):
    return CommandLevels.TRUSTED


# I want to move some other functions here so they're shared across all plugins in later PR
class BasePlugin(Plugin):
    _shallow = True

    def __init__(self, bot, config):
        super(BasePlugin, self).__init__(bot, config)
        # I'd recommend using a test DB first? to see if works, then run it on prod
        self.client = MongoClient(
            self.config.mongodb_host,
            self.config.mongodb_port,
            username=self.config.mongodb_username,
            password=self.config.mongodb_password
        )
        self.users = self.client.experience.users
        self.actions = self.client.experience.actions

    def shared_add_xp(self, user_id, amount):
        uid = str(user_id)
        user = self.users.find_one({'user_id': uid})
        if user is None:
            user = {'user_id': uid, 'xp': 0}
            self.users.insert_one(user)
        total = user['xp'] + amount
        self.users.update_one({'user_id': uid}, {'$set': {'xp': total}})
