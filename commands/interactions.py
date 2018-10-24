#Welcome to the ChatInteractionPlugin!
#Most of the code here is proudly borrowed from experience.py due to the bots current setup. 
#If one person got it right, I won't reinvent the wheel.
import random

from disco.bot import Plugin
from pymongo import MongoClient

from commands.config import ChatInteractionsConfig

from util.GlobalHandlers import command_wrapper

@Plugin.with_config(ChatInteractionsConfig)
class ChatInteractionPlugin(Plugin):

    def load(self, ctx):
        super(ChatInteractionPlugin, self).load(ctx)
        self.client = MongoClient(self.config.mongodb_host, self.config.mongodb_port,
                                  username=self.config.mongodb_username,
                                  password=self.config.mongodb_password)
        self.database = self.client.get_database("experience")
        self.users = self.database.get_collection("users")
        self.actions = self.database.get_collection("actions")
        self.purchases = self.database.get_collection("purchases")
 
    def unload(self, ctx):
        self.users.save()
        self.actions.save()
        super(ChatInteractionPlugin, self).load(ctx)

    def get_user(self, id):
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

    def get_id(self, id_str):
        if id_str.isdigit():
            return int(id_str)
        elif id_str.startswith("<@") and id_str.endswith(">"):
            snowflake_str = id_str[2:-1]
            if snowflake_str.startswith("!"):
                snowflake_str = id_str[3:-1]
            return snowflake_str
        else:
            # invalid, returning None
            return None

    @Plugin.command("hug", "<user:user>")
    @command_wrapper(perm_lvl=1)
    def hug(self, event, user):
        member = event.guild.get_member(user)

        user = self.get_user(event.msg.author.id)

        if user["xp"] < self.config.hug_cost:
            event.msg.reply(":no_entry_sign: Sadly, you don't have enough XP to hug :(")
            return

        self.users.update_one({
            "user_id": str(event.msg.author.id)
        }, {
            "$set": {
                "xp": user["xp"] - self.config.hug_cost
            }
        })
        event.msg.reply("<@{}>, {} {}".format(member.id, event.msg.author.username, random.choice(self.config.hug_msgs)))

    @Plugin.command("fight", "<user:user>")
    @command_wrapper(perm_lvl=1)
    def fight(self, event, user):
        member = event.guild.get_member(user)

        user = self.get_user(event.msg.author.id)

        if user["xp"] < self.config.hug_cost:
            event.msg.reply(":no_entry_sign: Uhoh! You can't start a fight because you don't have enough XP :(")
            return

        self.users.update_one({
            "user_id": str(event.msg.author.id)
        }, {
            "$set": {
                "xp": user["xp"] - self.config.fight_cost
            }
        })
        event.msg.reply("{} is fighting <@{}>{}".format(event.msg.author.username, member.id, random.choice(self.config.fight_msgs)))        
