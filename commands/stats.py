import re
from datetime import datetime, timedelta
from functools import reduce

from disco.api.http import APIException
from disco.bot import Plugin
from disco.bot.command import CommandEvent
from disco.types import Message, Channel
from disco.types.message import MessageEmbed
from disco.util import snowflake

from commands.config import StatsPluginConfig
from util.GlobalHandlers import command_wrapper


@Plugin.with_config(StatsPluginConfig)
class StatsPlugin(Plugin):

    def __init__(self, bot, config):
        super().__init__(bot, config)
        self.channel_regex = re.compile('<#([0-9]{17,18})>\\s.*Reported:', re.MULTILINE)
        self.argument_regex = re.compile('{{([A-Za-z_]+):?([A-Za-z0-9,_/]+)?}}', re.MULTILINE)
        self.summary_message = None

    @Plugin.command('stats update')
    @command_wrapper(perm_lvl=2)
    def update_stats(self, event: CommandEvent):
        m = event.msg.reply(":timer: Updating Queue statistics...")
        self.update_queue_message()
        m.edit(":white_check_mark: Queue statistics updated!")

    def get_reporting_channel(self, msg: Message):
        match = self.channel_regex.findall(msg.content)
        if len(match) > 0:
            return match[0]
        else:
            return None

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
                reports[bug_report_channel] = [message]
            else:
                reports[bug_report_channel].append(message)
        return reports

    def parse_message(self, msg, reports):
        parsed = msg
        for match in self.argument_regex.finditer(msg):
            arg = match.group(0)
            name = match.group(1).lower()
            args = match.group(2).lower().split(",")
            resp = self.call_arguments(name, args, reports)
            parsed = parsed.replace(arg, resp)
        return parsed

    @Plugin.schedule(300, True, False)
    def update_queue_message(self):
        reports = self.get_all_bug_reports()
        message = "\n".join(self.config.queue_summary['message'])
        message = self.parse_message(message, reports)
        embed = MessageEmbed()
        embed.title = self.config.queue_summary['title']
        embed.color = int(self.config.queue_summary['color'].replace('#', ''), 16)
        embed.description = message
        embed.set_footer(text="Last updated at")
        embed.timestamp = datetime.utcnow().isoformat()
        self.send_or_update_message(embed)

    def send_or_update_message(self, embed: MessageEmbed):
        chan = self.bot.client.state.guilds[self.config.dtesters_guild_id].channels[
            self.config.queue_summary['channel']]
        if self.summary_message is None:
            # Look in the stats channel for a previous message by us
            for msg in chan.messages:
                if msg.author.id != self.state.me.id:
                    continue
                self.summary_message = msg

        if self.summary_message is None:
            chan.send_message(embed=embed)
        else:
            # Edit the message with the new content
            try:
                self.summary_message.edit(embed=embed)
            except APIException:
                # The message got deleted?
                self.summary_message = None
                self.send_or_update_message(embed)

    def call_arguments(self, argument_type, params, reports):
        attr_name = f"argument_{argument_type}"
        if hasattr(self, attr_name):
            return getattr(self, attr_name)(**{'params': params, 'reports': reports})
        else:
            return f"*Unknown argument {argument_type}*"

    def argument_oldest_report(self, params, reports: dict):
        r = reduce(list.__add__, reports.values()) if params[0] == "all" \
            else reports[params[0]] if params[0] in reports.keys() else []
        if len(r) == 0:
            return ""
        report = sorted(r, key=lambda x: x.id)[0]
        return f"https://discordapp.com/channels/{report.guild.id}/{report.channel.id}/{report.id}"

    def argument_total_reports(self, params, reports: dict):
        r = reduce(list.__add__, reports.values()) if params[0] == "all" \
            else reports[params[0]] if params[0] in reports.keys() else []
        return str(len(r))

    def argument_stale_reports(self, params, reports: dict):
        r = reduce(list.__add__, reports.values()) if params[0] == "all" \
            else reports[params[0]] if params[0] in reports.keys() else []
        hours = params[1]
        target = datetime.today() - timedelta(hours=int(hours))
        target_snowflake = snowflake.from_datetime(target)

        stale_reports = []
        for report in r:
            if report.id < target_snowflake:
                if report.edited_timestamp is not None:
                    if report.edited_timestamp < target:
                        stale_reports.append(report)
                else:
                    stale_reports.append(report)

        return str(len(stale_reports))
