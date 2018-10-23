import re
from datetime import datetime, timedelta
from functools import reduce

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
        self.argument_regex = re.compile('{{([A-Za-z_]+):?([A-Za-z0-9,_/]+)?}}', re.MULTILINE)

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
                to_add = f"<#{chan}> - **{len(reports)} report" + ("s" if len(reports) > 1 else "") + "**\n"
                if len(to_add + body) > 2000:
                    event.msg.reply(body)
                    body = ""
                body += to_add
            event.msg.reply(body)
        else:
            event.msg.reply("no reports in the queue?")

    @Plugin.command('argTest', '<msg:str...>')
    def arg_test(self, event: CommandEvent, msg: str):
        event.msg.reply(self.parse_message(msg, self.get_all_bug_reports()))

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
            self.bot.log.info(f"Parsing {arg} -- Name: {name}, args: {args}")
            resp = self.call_arguments(name, args, reports)
            parsed = parsed.replace(arg, resp)
        return parsed

    def call_arguments(self, argument_type, params, reports):
        self.bot.log.info(f"Executing argument_{argument_type}")
        return getattr(self, f"argument_{argument_type}")(**{'params': params, 'reports': reports})

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
