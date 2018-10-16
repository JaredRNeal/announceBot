import random
from disco import Plugin
from config import AnnounceBotConfig
from util.GlobalHandlers import command_wrapper, log_to_bot_log


class TestFlightConfig(AnnounceBotConfig):
    MENTOR_CHANNEL = ""
    HELP_MESSAGE = "{},{},{}"
    NO_MENTORS = "{},{}"
    MENTOR_ID = 487807730506006540
    LOG_MESSAGE = "{}"


@Plugin.with_config(TestFlightConfig)
class MentorPlugin(Plugin):
    def get_avail_mentors(self):
        return [u.user.id for u in self.bot.client.state.guilds.get(487611837664198679).members.values() if self.config.MENTOR_ID in u.roles and u.user.presence.status == "Online"]

    def ping_mentor(self, mentor, author, content):
        self.bot.client.state.channels.get(self.config.MENTOR_CHANNEL).send_message(self.config.HELP_MESSAGE.format(mentor, author, content))

    def send_to_mentor_channel(self, author, content):
        self.bot.client.state.channels.get(self.config.MENTOR_CHANNEL).send_message(self.config.NO_MENTORS.format(author, content))

    @Plugin.command("helpme", "<content:str...>")
    @command_wrapper(perm_lvl=1, allowed_in_dm=True, allowed_on_server=False)
    def on_help_command(self, event, content):
        mentors_available = self.get_avail_mentors()
        if mentors_available:
            self.ping_mentor(mentors_available[random.randint(0, len(mentors_available) - 1)], str(event.msg.author), content)
        else:
            self.send_to_mentor_channel(str(event.msg.author), content)
        log_to_bot_log(self.bot, self.config.LOG_MESSAGE.format(str(event.msg.author)))
