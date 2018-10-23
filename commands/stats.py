import re

from disco.bot import Plugin
from disco.bot.command import CommandEvent
from disco.types import Message, Channel
from disco.util import snowflake

from commands.config import StatsPluginConfig


@Plugin.with_config(StatsPluginConfig)
class StatsPlugin(Plugin):

    def __init__(self, bot, config):
        super().__init__(bot, config)
        self.channel_regex = re.compile('<#([0-9]{17,18})>\\s.*Reported:', re.MULTILINE)

    @Plugin.command('reportingChannel', '<chan_id:snowflake> <message_id:snowflake>')
    def reporting_channel(self, event: CommandEvent, chan_id, message_id):
        chan: Channel = event.guild.channels.get(chan_id)
        msg = chan.get_message(message_id)
        if msg is None:
            event.msg.reply(f"The message with id ${message_id} was not found!")
            return
        else:
            chan = self.get_reporting_channel(msg)
            t = snowflake.to_datetime(message_id)
            event.msg.reply(
                f"The message was reported in {chan} <#{chan}> and was reported on {t.strftime('%Y-%m-%d %H:%m:%S')}")

    @Plugin.command('reports')
    def reports(self, event: CommandEvent):
        reports = self.get_all_bug_reports()
        if reports is not None:
            body = ""
            for chan, reports in reports.items():
                to_add = f"<#{chan}> - **{len(reports)} report" + ("s" if len(reports) > 1 else "")+"**\n"
                if len(to_add + body) > 2000:
                    event.msg.reply(body)
                    body = ""
                body += to_add
            event.msg.reply(body)
        else:
            event.msg.reply("no reports in the queue?")

    def get_reporting_channel(self, msg: Message):
        match = self.channel_regex.findall(msg.content)
        return match[0]

    def get_all_bug_reports(self):
        guild = self.bot.client.state.guilds[self.config.dtesters_guild_id]
        if guild is None:
            self.bot.log.error("Failed to find the guild")
            return None  # We're not in DTesters?
        channel: Channel = guild.channels[self.config.queue_channel]
        if channel is None:
            self.bot.log.error("Failed to find the bug approval queue channel")
            return None  # The guild doesn't have the configured bug-approval-queue channel
        reports = {}
        for message in channel.messages:
            if message.author.id != self.config.bug_bot_user_id:
                continue
            bug_report_channel = self.get_reporting_channel(message)
            if bug_report_channel is None:
                continue  # Failed the Regex.
            if bug_report_channel not in reports.keys():
                reports[bug_report_channel] = [message.id]
            else:
                reports[bug_report_channel].append(message.id)
        return reports
