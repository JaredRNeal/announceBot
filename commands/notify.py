import re
from enum import Flag

from disco.bot import Plugin
from pymongo import MongoClient
from disco.api.http import APIException
from disco.types.message import MessageEmbed

from commands.config import NotifyPluginConfig
from util.GlobalHandlers import command_wrapper, log_to_bot_log, handle_exception


class Scope(Flag):
    NONE = 0
    APPROVE = 1
    DENY = 2
    ATTACH = 4
    EDIT = 8
    APPROVED = 16
    DENIED = 32
    ALL = APPROVE | DENY | ATTACH | EDIT | APPROVED | DENIED


SCOPE_DATA = {
    'approve': (
        'New approval',
        'A Bug Hunter has approved {report}',
        r':thumbsup:\s\*{2}\w+#[0-9]{4}\*{2}\sapproved:\s\*{2}#([0-9]+)'
    ),
    'deny': (
        'New denial',
        'A Bug Hunter has denied {report}',
        r':thumbsdown:\s\*{2}\w+#[0-9]{4}\*{2}\sdenied:\s\*{2}#([0-9]+)'
    ),
    'attach': (
        'New attachment',
        '{report} has a new attachment',
        r':paperclip:.*?\*{2}#([0-9]+)\*{2}$'
    ),
    'edit': (
        'Report edited',
        '{report} has been edited',
        r':pencil2:\s\*{2}\w+#[0-9]{4}\*{2}\sedited\s\*{2}#([0-9]+)'
    ),
    'approved': (
        'Report approved',
        '{report} has been fully approved\n\nLink: {link}',
        r':incoming_envelope:.*?(https?://trello.com/c/[\w]+)>\s+([0-9]+)$'
    ),
    'denied': (
        'Report denied',
        '{report} has been denied',
        r'(?<=\s\*{2}#)[0-9]+'
    )
}


@Plugin.with_config(NotifyPluginConfig)
class NotifyPlugin(Plugin):

    def load(self, ctx):
        super(NotifyPlugin, self).load(ctx)
        self.client = MongoClient(self.config.mongodb_host, self.config.mongodb_port)
        self.reports = self.client.notify.reports
        self._compile_exp()

    def unload(self, ctx):
        self.reports.save()
        super(NotifyPlugin, self).unload(ctx)

    def _compile_exp(self):
        self.exp = {}
        for action, data in SCOPE_DATA.items():
            self.exp[action] = re.compile(data[2])

    @staticmethod
    def _get_scope_str(scopes):
        names = [s.name for s in Scope if s != Scope.NONE and s in scopes]
        return ','.join(names)

    @Plugin.command('get', group='notify')
    @command_wrapper(allowed_on_server=False, allowed_in_dm=True)
    def get_subscriptions(self, event):
        reports = self.reports.find({f'subs.{event.author.id}': {'$exists': True}})
        if len(reports) > 0:
            response = "You're registered for notifications for:\n"
            for r in reports:
                scope_str = self._get_scope_str(Scope(r['subs'][str(event.author.id)]))
                response += f"#{r['report_id']} - `{scope_str}`\n"
        else:
            response = "You aren't currently registered for any notifications"
        event.msg.reply(response)

    @Plugin.command('notify', '<report_id:int> [scopes:str...]')
    @command_wrapper(log=False, allowed_in_dm=True)
    def update_subscriptions(self, event, report_id, scopes=None):
        report = self.reports.find_one({'report_id': report_id})
        if report is not None:
            user_id = str(event.author.id)
            user_scopes = Scope(report['subs'].get(user_id, 0))
            old_scopes = user_scopes
            # User wants to clear notifications
            if scopes == 'clear':
                if user_scopes:
                    user_scopes = Scope.NONE
                    response = f"You'll no longer receive notifications for #{report_id}"
                else:
                    response = f"You haven't registered for notifications for #{report_id}"
            # User wants all notifications (or wants to reverse that)
            elif scopes is None:
                if user_scopes == Scope.ALL:
                    # Could be confusing but acts as a toggle for convenience
                    user_scopes = Scope.NONE
                    response = f"You'll no longer receive notifications for #{report_id}"
                else:
                    user_scopes = Scope.ALL
                    response = f"You'll receive all notifications for #{report_id}"
            # User wants specific notifications
            else:
                req_scopes = Scope.NONE
                # Try to parse the scopes they wanted
                try:
                    for s in scopes.split(','):
                        req_scopes |= Scope[s.upper()]
                except KeyError:
                    response = "I didn't recognise one or more of those scopes. Try `+notify <id>` to receive all notifications for a report"
                else:
                    if req_scopes != Scope.NONE:
                        if req_scopes in user_scopes:
                            response = f"You already have notifications for these scopes. You can use `+notify <id> clear` to remove them"
                        else:
                            user_scopes |= req_scopes
                            response = f"You'll receive `{self._get_scope_str(user_scopes)}` notifications for #{report_id}"
            # If they've made valid changes to their scopes
            if old_scopes != new_scopes:
                # Removed
                if user_scopes == Scope.NONE:
                    self.reports.update_one({'report_id': report_id}, {'$unset': {f'subs.{user_id}': ''}})
                    log_to_bot_log(self.bot, f':pager: {event.author} removed notifications for #{report_id}')
                # Added/Changed
                else:
                    scope_str = self._get_scope_str(user_scopes)
                    self.reports.update_one({'report_id': report_id}, {'$set': {f'subs.{user_id}': user_scopes.value}})
                    log_to_bot_log(self.bot, f':pager: {event.author} registered for `{scope_str}` notifications for #{report_id}')
            event.msg.reply(f'{event.author.mention} {response}').after(5).delete()
        else:
            event.msg.reply(f"{event.author.mention} I can't find that report ID").after(5).delete()
        event.msg.delete()

    @Plugin.listen('MessageCreate')
    def on_message_create(self, event):
        if event.author.id != self.config.bug_bot_id:
            return
        action = None
        # Bot Log - covers almost all events
        if event.channel.id == self.config.channels['bot-log']:
            # Try to find an event/action match for the message
            for act in self.exp:
                if act == 'denied':
                    continue
                match = self.exp[act].match(event.message.content)
                if match:
                    if act == 'approved':
                        link = match.group(1)
                        report_id = int(match.group(2))
                    else:
                        report_id = int(match.group(1))
                    action = act
                    break
        # Denied Bugs - only denied tickets
        elif event.channel.id == self.config.channels['denied-bugs']:
            try:
                report_id = int(self.exp['denied'].search(event.message.content).group(0))
            except AttributeError as e:
                # Couldn't extract the report ID from the message
                handle_exception(event, self.bot, e)
            else:
                action = 'denied'
        # Approval Queue - to track new tickets
        elif event.channel.id == self.config.channels['bug-approval-queue']:
            search = re.findall(r'(?<=Report\sID:\s\*{2})[0-9]+', event.message.content)
            if search:
                try:
                    # Get the last ID in case the report includes the format above
                    report_id = int(search[-1])
                except IndexError as e:
                    # Couldn't extract the report ID from the message
                    handle_exception(event, self.bot, e)
                else:
                    self.reports.insert_one({'report_id': report_id, 'subs': {}})
        if action is not None:
            report = self.reports.find_one({'report_id': report_id})
            if report is not None:
                if len(report['subs']) > 0:
                    action_scope = Scope[action.upper()]
                    report_str = f'Report **#{report_id}**'
                    if action == 'approved':
                        msg = SCOPE_DATA[action][1].format(report=report_str, link=link)
                    else:
                        msg = SCOPE_DATA[action][1].format(report=report_str)
                    em = MessageEmbed()
                    em.title = f'{SCOPE_DATA[action][0]} (#{report_id})'
                    em.description = msg
                    em.color = '7506394'
                    uc = 0
                    for k, v in report['subs'].items():
                        if action_scope & Scope(v):
                            dm = self.bot.client.api.users_me_dms_create(int(k))
                            try:
                                dm.send_message(embed=embed)
                            except APIException:
                                # Closed DMs
                                pass
                            else:
                                uc += 1
                    if uc > 0:
                        log_to_bot_log(self.bot, f':pager: `{action}` notification for **#{report_id}** sent to {uc} user(s)')
                if action in ['approved', 'denied']:
                    self.reports.delete_one({'report_id': report_id})
