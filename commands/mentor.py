import time
import random
from datetime import datetime

from pymongo import MongoClient
from bson.objectid import ObjectId
from bson.errors import InvalidId
from disco.bot import Plugin
from disco.util import sanitize
from disco.types.base import UNSET
from disco.types.user import Status
from disco.api.http import APIException
from disco.types.message import MessageEmbed

from commands.config import AnnounceBotConfig
from util.GlobalHandlers import command_wrapper, log_to_bot_log


class MentorConfig(AnnounceBotConfig):

    channels = {
        "mentor": 471421747669762048,
        "new_bh": 473944829919887371,
        "mod": 0
    }
    messages = {
        "no_mentors": "{} requested help with `{}` however there are currently no available mentors online. React below if you'd like to help them",
        "new_bh_join": "<@{}> just joined the Bug Hunters! React below if you'd like to mentor them.",
        "log_started_mentoring": "<@{}> has started mentoring <@{}>!",
        "no_bh_mentors": "<@{}> just joined the Bug Hunters but no one is available to mentor them!",
        "helpee_mentor_assigned": "{} has been assigned to help you. Look out for a DM from them shortly",
        "mod_helpme_escalated": "**{}** has escalated the following HelpMe request:\nID: {}\nHelpee: {}\nMessage: ```{}```",
        "helpee_already_open": "You already have a HelpMe request open. Please wait for a DM from a mentor or you can cancel using `+helpme cancel`",
        "helpee_helpme_complete": "Your mentor has marked this HelpMe request as complete. We'd really appreciate it if you could fill out this survey to let us know how it went: {}",
        "mentor_helpme_complete": "XP deposited! Thanks for helping out :)",
        "log_helpme_complete": "{} completed a HelpMe request from {}",
        "helpee_delay": "Sorry, there's been a slight delay in finding an available mentor to help. We'll get someone to contact you as soon as possible",
        "mentor_declined": "You have declined this HelpMe request so it will be passed to another mentor",
        "mentor_escalated": "This HelpMe request has been escalated to DTesters mods",
        "mentor_claim_failed": "{} Your DMs are closed so you can't claim this request"
    }
    emoji = {
        "complete": {
            "name": "greenTick",
            "id": 312314752711786497
        },
        "decline": {
            "name": "redTick",
            "id": 312314733816709120
        },
        "escalate": {
            "name": "discordPolice",
            "id": 233444108658671616
        },
        "mentor": {
            "name": "dabPingWordless",
            "id": 456143314404769793
        }
    }
    join_phrase = "to the Bug Hunters:tm:!"
    mentor_role_id = 502115003445411840
    helpme_embed_desc = ["You've been selected to assist with the following HelpMe request",
                         "",
                         "Please DM the user directly to assist and then react as necessary once complete:",
                         "<:{}> - I have finished helping the user",
                         "<:{}> - I am unavailable. Please pass this request to another mentor",
                         "<:{}> - This request needs to be escalated to DTesters mods"]
    survey_link = 'https://dabbit.typeform.com/to/mnlaDU?id={}'
    helpme_xp = 1


@Plugin.with_config(MentorConfig)
class MentorPlugin(Plugin):

    def load(self, ctx):
        super().load(ctx)
        self.client = MongoClient(self.config.mongodb_host, self.config.mongodb_port,
                                  username=self.config.mongodb_username,
                                  password=self.config.mongodb_password)
        self.helpme = self.client.mentors.helpme
        self.users = self.client.experience.users

    def unload(self, ctx):
        super().unload(ctx)
        self.helpme.save()
        self.users.save()

    def add_xp(self, user_id, amount):
        uid = str(user_id)
        user = self.users.find_one({'user_id': uid})
        if user is None:
            user = {'user_id': uid, 'xp': 0}
            self.users.insert_one(user)
        total = user['xp'] + amount
        self.users.update_one({'user_id': uid}, {'$set': {'xp': total}})
        log_to_bot_log(self.bot, f':pencil: Updated point total for {uid} to {total} for completing a HelpMe request')

    def get_mentor(self, exclude=[]):
        guild = self.bot.client.state.guilds.get(self.config.dtesters_guild_id)
        mentors = [u.user for u in guild.members.values() if self.config.mentor_role_id in u.roles and u.user.id not in exclude and u.user.presence is not UNSET and u.user.presence.status == Status.ONLINE]
        if mentors:
            # TODO: Could make this round robin?
            return random.choice(mentors)
        else:
            return None

    def build_emoji(self, emoji):
        ed = self.config.emoji.get(emoji, None)
        if ed:
            return f'{ed["name"]}:{ed["id"]}'
        return None

    def build_help_embed(self, helpee_mention, query, identifier):
        em = MessageEmbed()
        em.title = 'HelpMe Request'
        desc = '\n'.join(self.config.helpme_embed_desc)
        em.description = desc.format(self.build_emoji('complete'), self.build_emoji('decline'), self.build_emoji('escalate'))
        em.color = '7506394'
        em.set_footer(text=f'ID: {identifier}')
        em.add_field(name='Helpee', value=helpee_mention)
        em.add_field(name='Query', value=f'```{query}```')
        return em

    def send_dm(self, user_id, *args, **kwargs):
        dm = self.state.dms.get(user_id, self.bot.client.api.users_me_dms_create(user_id))
        try:
            msg = dm.send_message(*args, **kwargs)
        except APIException:
            return False
        else:
            return msg

    def get_user(self, user_id):
        user = self.state.users.get(user_id, None)
        if user is None:
            try:
                user = self.state.guilds.get(self.config.dtesters_guild_id).members.get(user_id).user
            # TODO: Fix this so it isn't a bare except
            except:
                user = None
        return user

    def assign_helpme(self, helpee, query, session_id, history, message=None, excluded=[]):
        mentor_id = 0
        while True:
            mentor_user = self.get_mentor(excluded)
            # Found a mentor
            if mentor_user:
                em = self.build_help_embed(helpee.mention, query, session_id)
                mentor_msg = self.send_dm(mentor_user.id, embed=em)
                if not mentor_msg:
                    # Mentor closed their DMs
                    log_to_bot_log(self.bot, f':shield: {mentor_user} was selected to assist but has closed DMs')
                    history.append((time.time(), 'declined', mentor_user.id))
                    excluded.append(mentor_user.id)
                else:
                    for reaction in [self.build_emoji('complete'), self.build_emoji('decline'), self.build_emoji('escalate')]:
                        mentor_msg.add_reaction(reaction)
                    helpee_msg = self.config.messages['helpee_mentor_assigned'].format(mentor_user.mention)
                    if message is None:
                        self.send_dm(helpee.id, helpee_msg)
                    else:
                        message.reply(helpee_msg)
                    mentor_id = mentor_user.id
                    history.append((time.time(), 'assigned', mentor_id))
                    log_suffix = f'{mentor_user} was assigned to assist'
                    break
            # No mentors available :(
            else:
                if message is None:
                    self.send_dm(helpee.id, self.config.messages['helpee_delay'])
                else:
                    message.reply(self.config.messages['helpee_delay'])
                mentor_msg = self.bot.client.api.channels_messages_create(self.config.channels['mentor'], self.config.messages['no_mentors'].format(helpee.mention, query))
                mentor_msg.add_reaction(self.build_emoji('complete'))
                history.append((time.time(), 'waiting', 0))
                log_suffix = 'no mentors available'
                break
        return {'mentor_id': mentor_id, 'message_id': mentor_msg.id, 'history': history, 'suffix': log_suffix}

    @Plugin.command("cancel", group="helpme")
    @command_wrapper(log=False, perm_lvl=1, allowed_in_dm=True, allowed_on_server=False)
    def cancel_help_request(self, event):
        session = self.helpme.find_one({'$and': [{'helpee_id': event.author.id}, {'active': True}]})
        if session:
            last_event = session['history'][-1][1]
            if last_event == 'waiting':
                try:
                    self.bot.client.api.channels_messages_delete(self.config.channels['mentor'], session['status_message_id'])
                except APIException:
                    pass
            elif last_event == 'assigned':
                self.send_dm(session['mentor_id'], f'{event.author} cancelled their HelpMe request')
            session['history'].append((time.time(), 'cancelled', event.author.id))
            self.helpme.update_one({'_id': session['_id']}, {'$set': {'history': session['history'], 'active': False}})
            event.msg.reply(f'I have cancelled your open HelpMe request')
            log_to_bot_log(self.bot, f'{event.author} cancelled their HelpMe request ({str(session["_id"])})')
        else:
            event.msg.reply("You don't have an open HelpMe request")

    @Plugin.command("lookup", "<identifier:str>", group="helpme")
    @command_wrapper(allowed_in_dm=True)
    def lookup_help_session(self, event, identifier):
        try:
            session_id = ObjectId(identifier)
        except InvalidId:
            event.msg.reply('That identifier is in the wrong format')
        else:
            session = self.helpme.find_one({'_id': ObjectId(identifier)})
            if session:
                em = MessageEmbed()
                em.title = f'DTesters HelpMe Session ({identifier})'
                em.description = 'Details for the session are below'
                em.color = '7506394'
                helpee_user = self.get_user(session['helpee_id'])
                mentor_user = self.get_user(session['mentor_id'])
                helpee_name = str(helpee_user) if helpee_user else session['helpee_id']
                mentor_name = str(mentor_user) if mentor_user else session['mentor_id']
                if mentor_name == 0:
                    mentor_name = '<UNASSIGNED>'
                active = 'Yes' if session['active'] else 'No'
                em.add_field(name='Helpee', value=helpee_name, inline=True)
                em.add_field(name='Mentor', value=mentor_name, inline=True)
                em.add_field(name='Active', value=active, inline=True)
                em.add_field(name='Query', value=f'```{session["query"]}```')
                history = []
                for entry in session['history']:
                    tstr = datetime.utcfromtimestamp(entry[0]).strftime('%Y-%m-%d %H:%M:%S')
                    actor = 0
                    if entry[2] != 0:
                        actor = self.get_user(entry[2])
                        if actor:
                            actor = str(actor)
                        else:
                            actor = entry[2]
                    history_map = {
                        'received': 'HelpMe used',
                        'declined': '{} declined',
                        'assigned': 'Assigned to {}',
                        'waiting': 'Posted in mentor channel',
                        'complete': '{} completed the request',
                        'escalated': '{} escalated to the mods'
                    }
                    hmsg = history_map.get(entry[1], 'Unknown event').format(actor)
                    history.append(f'{tstr} - {hmsg}')
                em.add_field(name='History', value='\n'.join(history))
                event.msg.reply(embed=em)
            else:
                event.msg.reply('Unable to find a session with that identifier')

    @Plugin.command("helpme", "<content:str...>")
    @command_wrapper(log=False, perm_lvl=1, allowed_in_dm=True, allowed_on_server=False)
    def on_help_command(self, event, content):
        if not self.helpme.find_one({'$and': [{'helpee_id': event.author.id}, {'active': True}]}):

            content = sanitize.S(content, escape_codeblocks=True)
            history = [(time.time(), 'received', 0)]
            session_id = ObjectId()
            assignment = self.assign_helpme(event.author, content, session_id, history, event.msg)

            # Add session to the DB
            self.helpme.insert_one({
                '_id': session_id,
                'active': True,
                'helpee_id': event.author.id,
                'mentor_id': assignment['mentor_id'],
                'query': content,
                'history': assignment['history'],
                'status_message_id': assignment['message_id']
            })
            log_to_bot_log(self.bot, f'{event.author} used the HelpMe command ({assignment["suffix"]})')
        else:
            event.msg.reply(self.config.messages['helpee_already_open'])

    @Plugin.listen("MessageCreate")
    def on_message_create(self, event):

        # If the bot does the thing in the right channel, check what mentors are available.
        if self.config.join_phrase in event.content and event.channel_id == self.config.channels['new_bh']:
            the_chosen_one = self.get_mentor()
        else:
            return
        # If there's at least one mentor in the list, ping them.
        if the_chosen_one is None:
            self.bot.client.api.channels_messages_create(self.config.channels['mentor'], self.config.messages['no_bh_mentors'].format(event.content[10:28]))
            log_to_bot_log(self.bot, self.config.messages['no_bh_mentors'].format(event.content[10:28]))
            return
        react_message = self.bot.client.api.channels_messages_create(self.config.channels['mentor'], self.config.messages['new_bh_join'].format(event.content[10:28], the_chosen_one.id))
        self.bot.client.api.channels_messages_reactions_create(self.config.channels['mentor'], react_message.id, self.build_emoji('mentor'))

    @Plugin.listen("MessageReactionAdd")
    def on_reaction(self, event):
        # Used to check if this is a DM
        try:
            gc = event.guild
        except AttributeError:
            gc = None

        # Ignore if we're the one reacting
        if event.user_id == self.state.me.id:
            return

        if event.channel_id == self.config.channels['mentor']:
            # A mentor is picking up a waiting HelpMe request
            if event.emoji.id == self.config.emoji['complete']['id']:
                session = self.helpme.find_one({'$and': [{'status_message_id': event.message_id}, {'active': True}]})
                if session:
                    mentor_user = self.get_user(event.user_id)
                    helpee_user = self.get_user(session['helpee_id'])
                    em = self.build_help_embed(helpee_user.mention, session['query'], str(session['_id']))
                    mentor_msg = self.send_dm(event.user_id, embed=em)
                    if not mentor_msg:
                        # Mentor has closed DMs
                        self.bot.client.api.channels_messages_create(self.config.channels['mentor'], self.config.messages['mentor_claim_failed'].format(mentor_user.mention)).after(5).delete()
                    else:
                        # Delete the message so no other mentors can claim it
                        self.bot.client.api.channels_messages_delete(self.config.channels['mentor'], event.message_id)
                        log_to_bot_log(self.bot, f'{mentor_user} picked up a HelpMe request from {helpee_user}')

                        for reaction in [self.build_emoji('complete'), self.build_emoji('decline'), self.build_emoji('escalate')]:
                            mentor_msg.add_reaction(reaction)

                        self.send_dm(session['helpee_id'], self.config.messages['helpee_mentor_assigned'].format(mentor_user.mention))

                        session['history'].append((time.time(), 'assigned', event.user_id))
                        self.helpme.update_one({'_id': session['_id']}, {'$set': {'history': session['history'], 'mentor_id': event.user_id, 'status_message_id': mentor_msg.id}})

            else:
                react_length = len(self.bot.client.api.channels_messages_reactions_get(self.config.channels['mentor'], event.message_id, self.build_emoji('mentor')))
                if react_length < 3:
                    event_message = self.bot.client.api.channels_messages_get(self.config.channels['mentor'], event.message_id)
                    log_to_bot_log(self.bot, self.config.messages['log_started_mentoring'].format(event.user_id, event_message.content[2:20]))

        # If it's a DM
        elif gc is None:
            session = self.helpme.find_one({'$and': [{'status_message_id': event.message_id}, {'active': True}]})
            if session:
                # The mentor has marked the request as complete
                if event.emoji.id == self.config.emoji['complete']['id']:
                    self.helpme.update_one({'_id': session['_id']}, {'$set': {'status_message_id': 0}})

                    helpee_user = self.get_user(session['helpee_id'])
                    mentor_user = self.get_user(session['mentor_id'])
                    log_to_bot_log(self.bot, self.config.messages['log_helpme_complete'].format(mentor_user, helpee_user))

                    # Send DM to helpee with survey link
                    link = self.config.survey_link.format(str(session['_id']))
                    self.send_dm(session['helpee_id'], self.config.messages['helpee_helpme_complete'].format(link))

                    # Update mentor's XP
                    self.add_xp(session['mentor_id'], self.config.helpme_xp)

                    self.send_dm(session['mentor_id'], self.config.messages['mentor_helpme_complete'])

                    session['history'].append((time.time(), 'complete', session['mentor_id']))
                    self.helpme.update_one({'_id': session['_id']}, {'$set': {'active': False, 'history': session['history']}})

                # The mentor declined the request
                elif event.emoji.id == self.config.emoji['decline']['id']:
                    self.helpme.update_one({'_id': session['_id']}, {'$set': {'status_message_id': 0}})

                    # Add current mentor to declined history
                    session['history'].append((time.time(), 'declined', event.user_id))

                    # Get declined events from session history
                    excluded = [x[2] for x in session['history'] if x[1] == 'declined']

                    self.send_dm(session['mentor_id'], self.config.messages['mentor_declined'])

                    # Find a new mentor
                    helpee = self.get_user(session['helpee_id'])
                    assignment = self.assign_helpme(helpee, session['query'], str(session['_id']), session['history'], excluded=excluded)

                    self.helpme.update_one({'_id': session['_id']}, {'$set': {'history': assignment['history'], 'mentor_id': assignment['mentor_id'], 'status_message_id': assignment['message_id']}})

                # The mentor escalated to the mods
                elif event.emoji.id == self.config.emoji['escalate']['id']:
                    self.helpme.update_one({'_id': session['_id']}, {'$set': {'status_message_id': 0}})
                    self.send_dm(session['mentor_id'], self.config.messages['mentor_escalated'])

                    # Post details in mod chat
                    mentor_user = self.get_user(session['mentor_id'])
                    helpee_user = self.get_user(session['helpee_id'])
                    self.bot.client.api.channels_messages_create(self.config.channels['mod'], self.config.messages['mod_helpme_escalated'].format(mentor_user.mention, str(session['_id']), helpee_user.mention, session['query']))

                    session['history'].append((time.time(), 'escalated', session['mentor_id']))
                    self.helpme.update_one({'_id': session['_id']}, {'$set': {'active': False, 'history': session['history']}})
                    log_to_bot_log(self.bot, f'{mentor_user} escalated a HelpMe request from {helpee_user}')
