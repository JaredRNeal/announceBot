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
        r':thumbsup:\s\*{2}.+?#[0-9]{4}\*{2}\sapproved:\s\*{2}#([0-9]+)'
    ),
    'deny': (
        'New denial',
        'A Bug Hunter has denied {report}',
        r':thumbsdown:\s\*{2}.+?#[0-9]{4}\*{2}\sdenied:\s\*{2}#([0-9]+)'
    ),
    'attach': (
        'New attachment',
        '{report} has a new attachment',
        r':paperclip:.*?\*{2}#([0-9]+)\*{2}$'
    ),
    'edit': (
        'Report edited',
        '{report} has been edited',
        r':pencil2:\s\*{2}.+?#[0-9]{4}\*{2}\sedited\s\*{2}#([0-9]+)'
    ),
    'approved': (
        'Report approved',
        '{report} has been fully approved',
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
        self.client = MongoClient(self.config.mongodb_host, self.config.mongodb_port,
                                  username=self.config.mongodb_username,
                                  password=self.config.mongodb_password)
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
        names = [s.name for s in Scope if s not in [Scope.NONE, Scope.ALL] and s in scopes]
        return ','.join(names)

    @staticmethod
    def _build_jump_link(guild_id, channel_id, message_id):
        return f'https://discordapp.com/channels/{guild_id}/{channel_id}/{message_id}'

    @Plugin.command('sync', group='notify')
    @command_wrapper(log=False)
    def sync_queue(self, event):
        queue = event.guild.channels[self.config.channels['bug-approval-queue']]
        reports = []
        for message in queue.messages:
            if message.author.id == self.config.bug_bot_user_id:
                search = re.findall(r'(?<=Report\sID:\s\*{2})[0-9]+', message.content)
                if search:
                    report_id = int(search[-1])
                    if not self.reports.find_one({'report_id': report_id}):
                        reports.append({'report_id': report_id, 'subs': {}, 'queue_msg': message.id})
        if len(reports) > 0:
            self.reports.insert_many(reports)
        log_to_bot_log(self.bot, f':envelope_with_arrow: {event.author} triggered a notify sync. {len(reports)} unseen reports added to the database')
        event.msg.delete()

    @Plugin.command('get', group='notify')
    @command_wrapper(perm_lvl=0, allowed_on_server=False, allowed_in_dm=True)
    def get_subscriptions(self, event):
        rl = []
        reports = self.reports.find({f'subs.{event.author.id}': {'$exists': True}})
        for r in reports:
            scope_str = self._get_scope_str(Scope(r['subs'][str(event.author.id)]))
            rl.append(f"#{r['report_id']} - `{scope_str}`")
        if len(rl) > 0:
            response = "You're registered for notifications for:\n"
            response += '\n'.join(rl)
        else:
            response = "You aren't currently registered for any notifications"
        event.msg.reply(response)

    @Plugin.command('notify', '<report_id:int> [scopes:str...]')
    @command_wrapper(perm_lvl=0, log=False, allowed_in_dm=True)
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
            if old_scopes != user_scopes:
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
        if not event.msg.channel.is_dm:
            event.msg.delete()

    @Plugin.listen('MessageCreate')
    def on_message_create(self, event):
        if event.author.id != self.config.bug_bot_user_id:
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
                # Get the last ID in case the report includes the format above
                report_id = int(search[-1])
                self.reports.insert_one({'report_id': report_id, 'subs': {}, 'queue_msg': event.message.id})
        # Check if we need to send a DM update
        if action is not None:
            report = self.reports.find_one({'report_id': report_id})
            if report is not None:
                if len(report['subs']) > 0:
                    action_scope = Scope[action.upper()]
                    # Linkify the report ID
                    if action == 'approved':
                        report_str = f'report [**#{report_id}**]({link})'
                    elif action == 'denied':
                        report_str = f'report **#{report_id}**'
                    else:
                        link = self._build_jump_link(event.guild.id, self.config.channels['bug-approval-queue'], report['queue_msg'])
                        report_str = f'report [**#{report_id}**]({link})'
                    em = MessageEmbed()
                    em.title = f'{SCOPE_DATA[action][0]} (#{report_id})'
                    em.description = SCOPE_DATA[action][1].format(report=report_str).capitalize()
                    em.color = '7506394'
                    uc = 0
                    for k, v in report['subs'].items():
                        if action_scope & Scope(v):
                            dm = self.bot.client.api.users_me_dms_create(int(k))
                            try:
                                dm.send_message(embed=em)
                            except APIException:
                                # Closed DMs
                                pass
                            else:
                                uc += 1
                    if uc > 0:
                        log_to_bot_log(self.bot, f':pager: `{action.upper()}` notification for **#{report_id}** sent to {uc} user(s)')
                if action in ['approved', 'denied']:
                    self.reports.delete_one({'report_id': report_id})
