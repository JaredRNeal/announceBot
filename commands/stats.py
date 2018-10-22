import re

from disco.bot import Plugin
from disco.bot.command import CommandEvent
from disco.types import Message, Channel

from commands.config import StatsPluginConfig


@Plugin.with_config(StatsPluginConfig)
class StatsPlugin(Plugin):

    def __init__(self, bot, config):
        super().__init__(bot, config)
        self.channel_regex = re.compile('<#([0-9]{17,18})>\s.*Reported:', re.MULTILINE)

    @Plugin.command('reportingChannel', '<chan_id:snowflake> <message_id:snowflake>')
    def reporting_channel(self, event: CommandEvent, chan_id, message_id):
        chan: Channel = event.guild.channels.get(chan_id)
        msg = chan.get_message(message_id)
        if msg is None:
            event.msg.reply(f"The message with id ${message_id} was not found!")
            return
        else:
            chan = self.get_reporting_channel(msg)
            event.msg.reply(f"The message was reported in {chan} <#{chan}>")

    def get_reporting_channel(self, msg: Message):
        print(msg.content)
        match = self.channel_regex.findall(msg.content)
        return match[0]
