import random
from disco.bot import Plugin
from commands.config import AnnounceBotConfig
from util.GlobalHandlers import command_wrapper, log_to_bot_log


class TestFlightConfig(AnnounceBotConfig):
    MENTOR_CHANNEL = "471421747669762048"
    HELP_MESSAGE = "<@{}>, {} has requested your help with: {}"
    NO_MENTORS = "{} requested help with `{}` however there are currently no available mentors online."
    MENTOR_ID = 502115003445411840
    LOG_MESSAGE = "{} used the HelpMe command."


@Plugin.with_config(TestFlightConfig)
class MentorPlugin(Plugin):
    def get_avail_mentors(self):
        return [u.user.id for u in self.bot.client.state.guilds.get(197038439483310086).members.values() if self.config.MENTOR_ID in u.roles and hasattr(u.user.presence, "status") and str(u.user.presence.status) == "online"]

    def ping_mentor(self, mentor, author, content):
        self.bot.client.api.channels_messages_create(self.config.MENTOR_CHANNEL, (self.config.HELP_MESSAGE.format(mentor, author, content)))

    def send_to_mentor_channel(self, author, content):
        self.bot.client.api.channels_messages_create(self.config.MENTOR_CHANNEL, (self.config.NO_MENTORS.format(author, content)))

    @Plugin.command("helpme", "<content:str...>")
    @command_wrapper(perm_lvl=1, allowed_in_dm=True, allowed_on_server=False)
    def on_help_command(self, event, content):
        mentors_available = self.get_avail_mentors()
        if mentors_available:
            self.ping_mentor(mentors_available[random.randint(0, len(mentors_available) - 1)], str(event.msg.author), content)
        else:
            self.send_to_mentor_channel(str(event.msg.author), content)
        log_to_bot_log(self.bot, self.config.LOG_MESSAGE.format(str(event.msg.author)))
