import requests
import random
from disco.bot import Bot,Plugin
from disco.types.message import MessageEmbed
from config import AnnounceBotConfig, TestPluginConfig

MENTOR_ID = 487807730506006540

@Plugin.with_config(TestPluginConfig)
class MentorPlugin(Plugin):

    def get_avail_mentors(self):
       return [u.user.id for u in self.bot.client.state.guilds.get(487611837664198679).members.values() if MENTOR_ID in u.roles and u.user.presence.status == "Online"]

    def ping_mentor(self, mentor, author, content):
        self.bot.client.state.channels.get(self.config.channel_IDs.get('MENTOR_CHANNEL')).send_message(self.config.messages.get("help_message").format(mentor, author, content))

    @Plugin.command("helpme", "<content:str...>")
    def on_help_command(self, event, content):
        if event.channel.is_dm:
            mentors_available = self.get_avail_mentors()
            if mentors_available:
                self.ping_mentor(mentors_available[random.randint(0, len(mentors_available) - 1)], str(event.msg.author), content)
            else:
                event.msg.reply(self.config.messages.get("no_mentors_available"))
