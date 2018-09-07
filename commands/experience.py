import time

from disco.bot import Plugin
from disco.types.message import MessageEmbed
from pymongo import MongoClient

from commands.config import ExperiencePluginConfig



@Plugin.with_config(ExperiencePluginConfig)
class ExperiencePlugin(Plugin):

    def load(self, ctx):
        super(ExperiencePlugin, self).load(ctx)
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
        super(ExperiencePlugin, self).load(ctx)

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

    def add_xp(self, id, points):
        user = self.get_user(str(id))
        user["xp"] += points
        return user

    def get_actions(self, user_id, type):
        return self.actions.find({"user_id": str(user_id), "type": type})

    def set_purchase_expired(self, purchase_id):
        self.purchases.update_one({
            "_id": purchase_id
        }, {
            "$set": {
                "expired": True
            }
        })

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

    def handle_action(self, user_id, action, has_time_limit):
        """ handles giving user XP for an action they did. """
        if has_time_limit:
            actions = []
            for action in self.get_actions(user_id, action):
                # if action happened less than 24 hours ago, add it.
                if action.get("time", 0) + 86400.0 >= time.time():
                    actions.append(action)
            if len(actions) >= self.config.reward_limits[action]:
                return
        user = self.get_user(user_id)
        self.users.update_one({
            "user_id": str(user_id)
        }, {
            "$set": {
                "xp": user["xp"] + self.config.rewards[action]
            }
        })
        if has_time_limit:
            self.actions.insert_one({
                "user_id": str(user_id),
                "type": action,
                "time": time.time()
            })

    @Plugin.schedule(3600, True, False)
    def remove_squasher_roles(self):
        t = time.time()
        purchases = self.purchases.find({
            "expired": False,
            "time": {
                "$lt": t - 604800.0
            },
            "type": "bug_squasher"
        })
        for purchase in purchases:
            print("[SQ] expired squasher role detected.")
            # purchase has expired.
            guild = self.bot.client.api.guilds_get(self.config.dtesters_guild_id)
            if not guild:  # if not in guild, wait until we are.
                print("[SQ] guild couldn't be found.")
                return
            member = guild.get_member(purchase["user_id"])
            # they left, so that means they don't have bug squasher
            if not member:
                self.set_purchase_expired(purchase["_id"])
                continue
            role = self.config.roles["squasher"]
            if role in member.roles:
                member.remove_role(role)
            self.set_purchase_expired(purchase["_id"])

    @Plugin.command("xp")
    def get_xp(self, event):
        if event.guild is not None:
            return

        DM = False
        if event.guild is None:
            DM = True

        # Check bug hunter
        dtesters = self.bot.client.api.guilds_get(self.config.dtesters_guild_id)
        member = dtesters.get_member(event.msg.author)
        if dtesters is None or member is None:
            return

        valid = False
        for role in member.roles:
            if role == self.config.roles.get("hunter"):
                valid = True

        if not valid:

            event.msg.reply("Sorry, only Bug Hunters are able to use the XP system. If you'd like to become a Bug Hunter, read all of <#342043548369158156>").after(5).delete()
            if DM == False:
                event.msg.delete()
            return

        # find the user's xp
        user = self.get_user(event.msg.author.id)
        xp = user["xp"]

        # show xp to user
        event.channel.send_message("<@{id}> you have {xp} XP!".format(id=str(event.msg.author.id), xp=xp))
        if DM == False:
            event.msg.delete()

    @Plugin.command("givexp", "<user_id:str> <points:int>")
    def give_xp(self, event, user_id, points):

        if not self.check_perms(event, "admin"):
            return

        uid = self.get_id(user_id)

        if uid is None:
            event.msg.reply(":no_entry_sign: invalid snowflake/mention").after(5).delete()
            return
        user = self.get_user(uid)

        if user["xp"] + points < 0:
            xp = 0
            self.users.update_one({
                "user_id": str(uid)
            }, {
                "$set": {
                    "xp": xp
                }
            })
            self.botlog(event, ":pencil: {mod} updated point total for {user} to {points}".format(
                mod=str(event.msg.author),
                user=str(uid),
                points=str(xp)
            ))
            event.msg.reply("User cannot have below 0 points, so set to 0.").after(5).delete()
            event.msg.delete()
            return
        xp = user["xp"] + points
        self.users.update_one({
            "user_id": str(uid)
        }, {
            "$set": {
                "xp": xp
            }
        })
        event.msg.reply(":ok_hand: {user} point total updated to {points}".format(user=str(uid), points=xp)) \
            .after(5).delete()
        event.msg.delete()
        self.botlog(event, ":pencil: {mod} updated point total for {user} to {points}".format(
            mod=str(event.msg.author),
            user=str(uid),
            points=str(xp)
        ))

    @Plugin.listen("MessageCreate")
    def message_listener(self, event):
        # Because we don't have Bug-bot access, we have to do it like this :(

        content = event.message.content
        if event.message.author.id != self.config.bug_bot_user_id:
            return
        long_repro_msg = "your repro has been successfully added to the Trello Ticket!"

        # handles approve/deny reports
        if "you've successfully approved report" in content or "you've successfully denied report" in content:
            if len(event.message.mentions) != 1:
                return
            for k in event.message.mentions.keys():
                self.handle_action(k, "approve_deny", True)
        # handles canrepro/cantrepro
        elif "your reproduction has been added to the ticket" in content or long_repro_msg in content:
            if len(event.message.mentions) != 1:
                return
            for k, v in event.message.mentions.items():
                self.handle_action(k, "canrepro_cantrepro", True)

        elif content.startswith(":incoming_envelope:"):
            if len(event.message.mentions) != 1:
                return
            for uid in event.message.mentions.keys():
                self.handle_action(uid, "submit", False)
        elif "your attachment has been added." in content:
            if len(event.message.mentions) != 1:
                return
            for uid in event.message.mentions.keys():
                self.handle_action(uid, "attach", True)

    @Plugin.command("store", aliases=['shop'])
    def store(self, event):
        if event.guild is not None:
            event.msg.delete()

        embed = MessageEmbed()
        embed.title = "Discord Testers Store"
        embed.description = "Use XP to get super cool Dabbit-approved rewards from the store!"
        embed.thumbnail.url = "https://cdn.discordapp.com/attachments/330341170720800768/471497246328881153/2Mjvv7E.png"
        embed.color = int(0xe74c3c)  # bug hunter red = #e74c3c

        index = 0
        for item in self.config.store:
            index = index + 1
            name = item["title"]
            content = "Cost: {cost}\nDescription: {description}\n{link}Buy this with `+buy {id}`".format(
                cost=item["cost"],
                description=item["description"],
                link="" if item.get("link", None) is None else "[Example]({link})\n".format(link=item["link"]),
                id=index
            )

            embed.add_field(name=name, value=content, inline=False)
        try:
            channel = event.msg.author.open_dm()
            channel.send_message("Store:", embed=embed)
        except:
            event.channel.send_message("please open your direct messages.").after(10).delete()

    @Plugin.command("buy", "<item:int>")
    def buy(self, event, item):
        # Check bug hunter
        dtesters = self.bot.client.api.guilds_get(self.config.dtesters_guild_id)
        if dtesters is None:
            return

        if event.guild is not None:
            event.msg.delete()

        member = dtesters.get_member(event.msg.author)
        if member is None:
            return

        valid = False
        for role in member.roles:
            if role == self.config.roles.get("hunter"):
                valid = True

        if not valid:
            return

        if len(self.config.store) < item or item < 1:
            event.msg.reply(":no_entry_sign: invalid store item! use `+store` to see the items!").after(10).delete()
            return

        store_item = self.config.store[item - 1]

        user = self.get_user(event.msg.author.id)

        if user["xp"] < store_item["cost"]:
            event.msg.reply(":no_entry_sign: you don't have enough XP to buy that!").after(10).delete()
            return
        self.users.update_one({
            "user_id": str(event.msg.author.id)
        }, {
            "$set": {
                "xp": user["xp"] - store_item["cost"]
            }
        })
        event.msg.reply(":ok_hand: item purchased! Note that if the item you purchased needs to be shipped, you have "
                        "to contact Dabbit Prime#0896 via DMs to provide a mailing address.").after(15).delete()
        prize_log_channel = self.bot.client.api.channels_get(self.config.channels["prize_log"])
        prize_log_channel.send_message("{name} (`{id}`) bought {title}!".format(
            name=str(event.msg.author),
            id=str(event.msg.author.id),
            title=store_item["title"]
        ))

        if store_item["id"] == "bug_squasher":
            self.bot.client.api.guilds_members_get(self.config.dtesters_guild_id, event.msg.author.id).add_role(
                event.guild.roles[self.config.roles["squasher"]])
        elif store_item["id"] == "fehlerjager_role":
            self.bot.client.api.guilds_members_get(self.config.dtesters_guild_id, event.msg.author.id).add_role(
                event.guild.roles[self.config.roles["fehlerjager"]])

        self.purchases.insert_one({
            "user_id": str(event.msg.author.id),
            "type": store_item["id"],
            "time": time.time(),
            "expired": False if store_item["id"] == "bug_squasher" else True
        })

    @Plugin.command("getxp", "<user_id:str>")
    def stats(self, event, user_id):
        if event.guild is None:
            return

        event.msg.delete()

        if not self.check_perms(event, "mod"):
            return

        uid = self.get_id(user_id)
        if uid is None:
            event.msg.reply(":no_entry_sign: invalid snowflake/mention.").after(5).delete()
            return
        user = self.get_user(uid)
        event.msg.reply("<@{uid}> has {xp} XP.".format(user=str(uid), xp=user["xp"])).after(10).delete()

    def check_perms(self, event, type):
        # get roles from the config
        roles = getattr(self.config, str(type) + '_roles').values()
        if any(role in roles for role in event.member.roles):
            return True
        event.msg.reply(":lock: You do not have permission to use this command!").after(5).delete()
        self.botlog(event, ":warning: " + str(
            event.msg.author) + " tried to use a command they do not have permission to use.")
        return False

    def botlog(self, event, message):
        channel = event.guild.channels[self.config.channels['bot_log']]
        channel.send_message(message)
