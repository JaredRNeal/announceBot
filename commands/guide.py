"""
A warning to anyone who tries to spend time fixing bugs:

I am terrible at naming variables. I spent 2 days attempting to fix
a bug when I was looking at my uncreative variable naming.
"""

import time
import math
import random
import os
import json

from disco.bot import Plugin
from disco.types.message import MessageEmbed

from commands.config import GuideConfig

from util.GlobalHandlers import command_wrapper, log_to_bot_log, handle_exception
from util import Pages


@Plugin.with_config(GuideConfig)
class GuidePlugin(Plugin):

    def load(self, ctx):
        super(GuidePlugin, self).load(ctx)
        Pages.register("guide", self.initialize_page, self.update_page)
        if not os.path.isfile("experiments.json"):
            self.experiments = { "dm-guide-on-join": 25 }
            return
        with open("experiments.json", "r") as experiments:
            # if this errors, dabbit didn't do the config right.
            self.experiments = json.loads(experiments.readline())

    def unload(self, ctx):
        Pages.unregister("guide")
        super(GuidePlugin, self).unload(ctx)

    def generate_page(self, page_number, guide):
        guide = self.config.guides[guide]
        max_page_number = len(guide["pages"])
        title = "{title} ({page}/{max_pages})".format(title=guide["title"], page=page_number, max_pages=max_page_number)
        description = guide["description"]
        embed = MessageEmbed()
        embed.title = title
        embed.description = description
        if page_number > max_page_number:
            embed.add_field(name="what??",
                            value="how did you get here? report this bug to brxxn#0632 or Dabbit Prime#0896.")
            return embed
        page = guide["pages"][page_number - 1]
        if page.get("color") is not None:
            embed.color = int(page["color"], 16)
        if page.get("image") is not None:
            embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/471128155214577670/504390962496143370/suffer.jpg")
        table_of_contents_field = None
        if "table_of_contents" in page:
            if page["table_of_contents"]:
                # Generate TOC
                table_of_contents = ""
                index = 0
                for item in guide["pages"]:
                    index = index + 1
                    table_of_contents = table_of_contents + "{page}. {title} - {description}\n".format(
                        page=str(index),
                        title=str(item["title"]),
                        description=str(item["description"])
                    )
                table_of_contents_field = {
                    "title": "Table of Contents",
                    "content": table_of_contents
                }
        embed.add_field(name=page["title"], value=page["description"])
        if table_of_contents_field is not None:
            embed.add_field(name=table_of_contents_field["title"], value=table_of_contents_field["content"])
        for field in page["fields"]:
            embed.add_field(name=field["name"], value=field["value"])
        return embed

    def initialize_page(self, channel, trigger, **kwargs):
        guide_message = self.config.welcome_message if kwargs.get("is_join_dm", False) else "Guide:"
        return guide_message, self.generate_page(1, kwargs["guide"]), len(self.config.guides[
                                                                            kwargs["guide"]
                                                                        ]) >= 2

    def update_page(self, message, page_num, action, data):
        if data.get("sender") is None:
            return
        pages = self.config.guides[data["guide"]]["pages"]
        page_count = len(pages)
        new_page_number = 1
        if action == "PREV":
            if page_num - 1 <= 0:
                new_page_number = len(pages)
            else:
                new_page_number = page_num
                new_page_number -= 1
        elif action == "NEXT":
            if page_num == len(pages):
                new_page_number = 1
            else:
                new_page_number = page_num
                new_page_number += 1
        return "Guide:", self.generate_page(new_page_number,  data["guide"]), new_page_number

    @Plugin.command("guide", "<guide_name:str>")
    @command_wrapper(perm_lvl=0, allowed_in_dm=True, allowed_on_server=False)
    def guide(self, event, guide_name):
        if self.config.guides.get(guide_name, "no-guide") == "no-guide":
            event.msg.reply(":no_entry_sign: couldn't find that guide. use `+guide list` to find guides.")
            return
        Pages.create_new(self.bot, "guide", event.channel, event.msg, page=1, guide=guide_name)

    @Plugin.command("list", group="guide")
    @command_wrapper(perm_lvl=0, allowed_in_dm=True, allowed_on_server=False)
    def list_guides(self, event):
        guide_list = "Guide List:\n\n"
        for k, v in self.config.guides.items():
            guide = "`+guide {name}` - {description}\n".format(name=k, description=v["description"])
            guide_list = guide_list + guide
        event.msg.reply(guide_list)
    
    @Plugin.command("dmchance", "<percent:float>")
    @command_wrapper(perm_lvl=2, allowed_in_dm=True, allowed_on_server=True)
    def set_dm_guide_percentage(self, event, percent):
        percent = percent / 100
        self.experiments["dm-guide-on-join"] = percent
        file = open("experiments.json", "w")
        file.write(json.dumps(self.experiments))
        file.close()
        event.msg.reply(":ok_hand: set dm guide percentage experimentation thing to `{percent}`".format(percent=percent * 100))
        log_to_bot_log(self.bot, ":wrench: DM Guide percentage updated to `{percent}` by {user}".format(percent=percent * 100, user=str(event.msg.author)))


    @Plugin.listen("GuildMemberAdd")
    def guide_send(self, event):
        randnum = random.random()
        print(str(randnum))
        if randnum <= self.experiments["dm-guide-on-join"]:
            try:
                channel = event.member.user.open_dm()
                Pages.create_new(self.bot, "guide", channel, page=1, guide="guide", is_join_dm=True)
                log_to_bot_log(self.bot, ":approve: Guide was successfully sent to {user}.".format(
                    user=str(event.member)
                ))
            except:
                log_to_bot_log(self.bot, ":no_entry_sign: {user} has DMs disabled, so the guide wasn't sent to them.".format(
                    user=str(event.member)
                ))
        
