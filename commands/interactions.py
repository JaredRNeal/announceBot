# Welcome to the ChatInteractionPlugin!
# Most of the code here is proudly borrowed from experience.py due to the bots current setup.
# If one person got it right, I won't reinvent the wheel.
import random
from commands.config import ChatInteractionsConfig

import requests
from disco.bot import Plugin
from disco.types.message import MessageEmbed
from pymongo import MongoClient

from util.GlobalHandlers import command_wrapper


@Plugin.with_config(ChatInteractionsConfig)
class ChatInteractionPlugin(Plugin):

    def load(self, ctx):
        super().load(ctx)
        self.client = MongoClient(self.config.mongodb_host, self.config.mongodb_port,
                                  username=self.config.mongodb_username,
                                  password=self.config.mongodb_password)
        self.database = self.client.get_database("experience")
        self.users = self.database.get_collection("users")
        self.actions = self.database.get_collection("actions")
        self.purchases = self.database.get_collection("purchases")

    def unload(self, ctx):
        super().unload(ctx)
        self.users.save()
        self.actions.save()

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

    @Plugin.command("bunny")
    @command_wrapper(perm_lvl=1)
    def bunny(self, event):
        user = self.get_user(event.msg.author.id)
        if user["xp"] < self.config.bunny_cost:
            return event.msg.reply(":no_entry_sign: sadly, you don't have enough XP for a cute bun bun. :(")
        self.users.update_one({
            "user_id": str(event.msg.author.id)
        }, {
            "$set": {
                "xp": user["xp"] - self.config.bunny_cost
            }
        })
        #r = requests.get("https://api.bunnies.io/v2/loop/random/?media=gif")
        r = requests.get("https://discordapp.com/jsjfjsjfkfkfkskdkfog")
        if r.status_code == 200:
            embed = MessageEmbed()
            bun_bun = r.json()
            embed.set_image(url=bun_bun['media']['gif'])
            event.msg.reply(embed=embed)
        else:
            event.msg.reply(":( Sorry, an unexpected error occurred when trying to display a bunny. Your XP has been refunded.")
            self.users.update_one({
                "user_id": str(event.msg.author.id)
            }, {
                "$set": {
                    "xp": user["xp"] + self.config.bunny_cost
                }
            })

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
        event.msg.reply(
            "<@{}>, {} {}".format(member.id, event.msg.author.username, random.choice(self.config.hug_msgs)))

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
        event.msg.reply("{} is fighting <@{}>{}".format(event.msg.author.username, member.id,
                                                        random.choice(self.config.fight_msgs)))

    # This is used for the mentors to check if a user is still in the server and to help cache them if they are.
    @Plugin.command("verify", "<UserID:int>")
    @command_wrapper(perm_lvl=1)
    def verify_user_in_server(self, event, UserID):
        # Only the mentors should be using this so limiting it to this channel.
        if event.channel.id != 471421747669762048:
            return
        Guild_Object = self.bot.client.state.guilds[197038439483310086]
        if UserID in Guild_Object.members.keys():
            event.msg.reply(f"The user with the ID {UserID} is still in the server! Maybe this helps cache them? <@{UserID}>. Their current username is {Guild_Object.members[UserID]}.")
        else:
            event.msg.reply(f"I cannot find a user with the ID {UserID}. They may have left the server already.")







#hello world
