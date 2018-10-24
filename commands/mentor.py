import random
from disco.bot import Plugin
from commands.config import AnnounceBotConfig
from util.GlobalHandlers import command_wrapper, log_to_bot_log


class MentorConfig(AnnounceBotConfig):
    MENTOR_CHANNEL = 471421747669762048
    HELP_MESSAGE = "<@{}>, {} has requested your help with: {}"
    NO_MENTORS = "{} requested help with `{}` however there are currently no available mentors online."
    MENTOR_ID = 502115003445411840
    LOG_MESSAGE = "{} used the HelpMe command."
    JOIN_PHRASE = "to the Bug Hunters:tm:!"
    NEW_BH_JOIN = "<@{}> just joined the Bug Hunters! React below if you'd like to mentor them."
    NEW_BH_CHANNEL = 473944829919887371
    SELF_ID = 413393370770046976
    MENTOR_LOG_MESSAGE = "<@{}> has started mentoring <@{}>!"
    MENTOR_EMOJI = ":dabPingWordless:456143314404769793"



@Plugin.with_config(MentorConfig)
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

    @Plugin.listen("MessageCreate")
    def on_message_create(self, event):

	#if the bot does the thing in the right channel, check what mentors are available.
        if self.config.JOIN_PHRASE in event.content and event.channel_id == self.config.NEW_BH_CHANNEL:
            mentors_available = self.get_avail_mentors()
        else:
            return
	#If there's at least one mentor in the list, ping them.
        if len(mentors_available) > 0:
            the_chosen_one = (mentors_available[random.randint(0, len(mentors_available) - 1)])
        else:
            self.bot.client.api.channels_messages_create(self.config.MENTOR_CHANNEL, self.config.NO_BH_MENTORS.format(event.content[10:28]))
            log_to_bot_log(self.bot, self.config.NO_BH_MENTORS.format(event.content[10:28]))
            return
        react_message = self.bot.client.api.channels_messages_create(self.config.MENTOR_CHANNEL, self.config.NEW_BH_JOIN.format(event.content[10:28], the_chosen_one))
        self.bot.client.api.channels_messages_reactions_create(self.config.MENTOR_CHANNEL, react_message.id, self.config.MENTOR_EMOJI)

    @Plugin.listen("MessageReactionAdd")
    def on_reaction(self, event):
        react_length = len(self.bot.client.api.channels_messages_reactions_get(self.config.MENTOR_CHANNEL, event.message_id, self.config.MENTOR_EMOJI))
        if event.channel_id == self.config.MENTOR_CHANNEL and event.user_id != self.config.SELF_ID and react_length < 3:
            event_message = self.bot.client.api.channels_messages_get(self.config.MENTOR_CHANNEL, event.message_id)
            log_to_bot_log(self.bot, self.config.MENTOR_LOG_MESSAGE.format(event.user_id, event_message.content[2:20]))
