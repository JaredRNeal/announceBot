import time
import math

from disco.api.http import APIException
from disco.bot import Plugin
from disco.types.message import MessageEmbed
from pymongo import MongoClient

from commands.config import ExperiencePluginConfig

from util.GlobalHandlers import command_wrapper, log_to_bot_log, handle_exception
from util import Pages


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
        Pages.register("xp_store", self.initialize_pages, self.update_page)

    def unload(self, ctx):
        self.users.save()
        self.actions.save()
        super(ExperiencePlugin, self).load(ctx)

    def initialize_pages(self, event):
        page_count = self.generate_page_count()
        return "Store:", self.generate_page(0, page_count - 1), page_count >= 2

    def update_page(self, message, page_num, action, data):
        page_count = self.generate_page_count()
        if action == "PREV":
            if page_num == 0:
                return "Store:", self.generate_page(page_count - 1, page_count - 1), page_count - 1
            new_page = page_num - 1
        else:
            if page_num + 2 > page_count:
                return "Store:", self.generate_page(0, page_count - 1), 0
            new_page = page_num + 1
        return "Store:", self.generate_page(new_page, page_count - 1), new_page

    def generate_store_embed(self, current, max):
        embed = MessageEmbed()
        embed.title = "Discord Testers Store ({current}/{max})".format(current=str(current + 1), max=str(max + 1))
        embed.description = "Use XP to get super cool Dabbit-approve:tm: rewards from the store!"
        embed.thumbnail.url = "https://cdn.discordapp.com/attachments/330341170720800768/471497246328881153/2Mjvv7E.png"
        embed.color = int(0xe74c3c)
        return embed

    def generate_page_count(self):
        item_length = len(self.config.store)
        return math.ceil(item_length / 2)

    def generate_page(self, current, max):
        items = self.generate_items(current * 2)
        embed = self.generate_store_embed(current, max)
        for item in items:
            name = item["title"]
            content = "Cost: {cost}\nDescription: {description}\n{link}Buy this with `+buy {id}`".format(
                cost=item["cost"],
                description=item["description"],
                link="" if item.get("link", None) is None else "[Example]({link})\n".format(link=item["link"]),
                id=item["id"] + 1
            )
            embed.add_field(name=name, value=content)
        return embed

    def generate_items(self, index):
        if len(self.config.store) <= index:
            return []
        fields = []
        i = 0
        for store_item in self.config.store:
            if index <= i < index + 2:
                store_item["id"] = i
                fields.append(store_item)
            i = i + 1
        return fields

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
        for previous_action in self.get_actions(user_id, action):
                # if action happened less than 24 hours ago, add it.
                if previous_action.get("time", 0) + 86400.0 >= time.time():
                    actions.append(previous_action)

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
            member = guild.get_member(str(purchase["user_id"]))
            # they left, so that means they don't have bug squasher
            if not member:
                self.set_purchase_expired(purchase["_id"])
                continue
            role = self.config.roles["squasher"]
            if role in member.roles:
                member.remove_role(role)
            log_to_bot_log("Removed the bug squasher role from {} as their purchase expired".format(str(member)))
            self.set_purchase_expired(purchase["_id"])

    @Plugin.command("xp")
    @command_wrapper(perm_lvl=0, allowed_on_server=False, allowed_in_dm=True, log=False)
    def get_xp(self, event):
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
            return

        # find the user's xp
        user = self.get_user(event.msg.author.id)
        xp = user["xp"]

        # show xp to user
        event.channel.send_message("<@{id}> you have {xp} XP!".format(id=str(event.msg.author.id), xp=xp))

    @Plugin.command("givexp", "<user_id:str> <points:int>")
    @command_wrapper(perm_lvl=2)
    def give_xp(self, event, user_id, points):
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
            log_to_bot_log(self.bot, ":pencil: {mod} updated point total for {user} to {points}".format(
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
        log_to_bot_log(self.bot, ":pencil: {mod} updated point total for {user} to {points}".format(
            mod=str(event.msg.author),
            user=str(uid),
            points=str(xp)
        ))

    @Plugin.listen("MessageCreate")
    def message_listener(self, event):
        # Because we don't have Bug-bot access, we have to do it like this :(
        try:
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
        except Exception as exception:
            handle_exception(event, self.bot, exception)

    @Plugin.command("store", aliases=['shop'])
    @command_wrapper(perm_lvl=0, allowed_on_server=False, allowed_in_dm=True)
    def store(self, event):
        Pages.create_new(self.bot, "xp_store", event)

    @Plugin.command("buy", "<item:int>")
    @command_wrapper(perm_lvl=0, allowed_in_dm=True, allowed_on_server=False)
    def buy(self, event, item):
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
                self.bot.client.state.guilds[self.config.dtesters_guild_id].roles[self.config.roles["squasher"]])
        elif store_item["id"] == "fehlerjager_role":
            self.bot.client.api.guilds_members_get(self.config.dtesters_guild_id, event.msg.author.id).add_role(
                self.bot.client.state.guilds[self.config.dtesters_guild_id].roles[self.config.roles["fehlerjager"]])

        self.purchases.insert_one({
            "user_id": str(event.msg.author.id),
            "type": store_item["id"],
            "time": time.time(),
            "expired": False if store_item["id"] == "bug_squasher" else True
        })

    @Plugin.command("getxp", "<user_id:str>")
    @command_wrapper()
    def stats(self, event, user_id):
        uid = self.get_id(user_id)
        if uid is None:
            event.msg.reply(":no_entry_sign: invalid snowflake/mention.").after(5).delete()
            return
        user = self.get_user(uid)
        event.msg.reply("<@{user}> has {xp} XP.".format(user=str(uid), xp=user["xp"])).after(10).delete()