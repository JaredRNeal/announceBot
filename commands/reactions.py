from commands.config import AnnounceBotConfig
from commands import BasePlugin
import re
import time


class ReactionConfig(AnnounceBotConfig):
    # This can be changed up
    msg_body = "TRELLO CARD:{}\n\nSCORE: {}"
    notable_metric = 5
    severity_metric = 3.5
    vote_value = 10
    eng_channel = 'TBD'
    base = "https://trello.com/c/"
    emojilist = {"1⃣": 1, "2⃣": 2, "3⃣": 3, "4⃣": 4, "5⃣": 5}
    emoji_keys = list(emojilist.keys())
    bug_channels = {
        'android': 413446997253554186,
        'iOS': 413447018816733195,
        'desktop': 413447049040756739,
        'store': 502206695611695134
    }


# This just adds reactions after checking whether a message is valid or not
@BasePlugin.with_config(ReactionConfig)
class ReactionPlugin(BasePlugin):
    # loads info from baseplugin and other useful items
    def load(self, ctx):
        super(ReactionPlugin, self).load(ctx)
        self.messages = self.client.reactions.messages
        self.reactors = self.client.reactions.reactors
        self.guild = self.bot.client.state.guilds.get(self.config.dtesters_guild_id)

    # checks if we want to look at a bb message (old, could be improved)
    def validatemessage(self, m):
        return((m.author.id == self.config.bug_bot_user_id and self.config.base in m.content) and m.channel.id in self.config.bug_channels.values())

    # adds reactions
    def addreact(self, m):
        counter = 0
        while counter < 5:
            m.add_reaction(list(self.config.emojilist.keys())[counter])
            counter += 1

    # every n seconds, sweeps recent (also variable) bugs, creates entries + sends to engineering
    # feel free to change 3000 to anything
    @BasePlugin.schedule(3000, True, False)
    def read_reactions(self):
        for channel in self.config.bug_channels.values():
            self.evaluate(channel, 30)

    # checks if it's a priority issue
    def is_priority(self, issue):
        is_notable = len(self.unique_users(issue)) >= self.config.notable_metric
        is_severe = self.aggregate_score(issue) >= self.config.severity_metric
        dne = self.messages.find_one({"testers_id": str(issue.id)}) is None
        return (dne and is_notable and is_severe)

    # checks if value changed since last sweep
    def did_value_change(self, issue):
        is_notable = len(self.unique_users(issue)) >= self.config.notable_metric
        is_severe = self.aggregate_score(issue) >= self.config.severity_metric
        exists = self.messages.find_one({"testers_id": str(issue.id)}) is not None
        if exists:
            score_change = self.messages.find_one({"testers_id": str(issue.id)}).get('score') != self.aggregate_score(issue)
        else:
            score_change = False
        return (exists and is_severe and is_notable and score_change)

    # actual mechanics of getting scores + sending to eng
    def evaluate(self, channel, limit):
        for message in self.bot.client.state.channels.get(channel).messages_iter(chunk_size=limit):
            # needs to meet criteria, message is priority, and not already in db
            if self.is_priority(message):
                card = re.match(r'https:\/\/trello.com\/c\/.+ -', message.content)
                trello_link = card.group(0)[:-2]
                # prints avg, for testing
                score = self.aggregate_score(message)
                # sends message to eng_channel
                eng_message = self.bot.client.api.channels_messages_create(self.config.eng_channel, self.config.msg_body.format(trello_link, score))
                # creates db entry
                self.add_message(message, eng_message, score)
            elif self.did_value_change(message):
                score = self.aggregate_score(message)
                self.messages.update_one({'testers_id': str(message.id)}, {'$set': {'score': score}})
                eng_msg = self.messages.find_one({'testers_id': str(message.id)})
                self.bot.client.api.channels_messages_modify(self.config.eng_channel, eng_msg.get('eng_id'), self.config.msg_body.format(score))

    # mongo aggregate that averages
    def aggregate_score(self, message):
        pipeline = [
            {'$match': {'testers_id': str(message.id)}},
            {'$group': {'_id': '$testers_id', 'total': {'$sum': '$score'}}}
        ]
        a = list(self.reactors.aggregate(pipeline))
        average = a[0].get('total')/len(self.unique_users(message)) if len(self.unique_users(message)) != 0 else 0
        return average

    # mongo aggregate that gets unique users
    def unique_users(self, message):
        pipeline = [
            {'$match': {'testers_id': str(message.id)}},
            {'$group': {'_id': '$reactor_id'}}
        ]
        return list(self.reactors.aggregate(pipeline))

    # adds reactors to db, tries to guarantee one entry in db and reaction at a time, awards xp for first vote only
    def add_reactor(self, channel_id, user_id, message_id, emoji):
        members = self.guild.members
        message = self.bot.client.api.channels_messages_get(channel_id, message_id)
        # this bit definitely could be better
        if self.config.role_IDs.get('bug') not in members.get(user_id).roles:
            return
        if str(members.get(user_id).user) not in message.content:
            return
        score = self.config.emojilist.get(emoji)
        react_base = {'reactor_id': str(user_id), 'testers_id': str(message_id)}
        reactor = {'reactor_id': str(user_id), 'testers_id': str(message_id), 'emoji': emoji, 'score': score}
        if self.reactors.find(react_base) is not None:
            for user in self.reactors.find(react_base):
                if user.get('emoji') != emoji:
                    self.bot.client.api.channels_messages_reactions_delete(channel_id, message_id, user.get('emoji'), user_id)
                    self.reactors.find_one_and_delete(user)
            self.reactors.insert_one(reactor)
        else:
            self.reactors.insert_one(reactor)
            if not self.actions.find_one({'user_id': str(user_id), 'type': 'vote', 'message_id': str(message_id)}):
                self.shared_add_xp(user_id, self.config.vote_value)
                self.actions.insert_one({
                    "user_id": str(user_id),
                    "type": 'vote',
                    "time": time.time(),
                    "message_id": str(message_id)
                    })

    # adds message entry to db
    def add_message(self, testers_message, eng_message, score):
        m_id = testers_message.id
        eng_id = eng_message.id
        card = re.match(r'https:\/\/trello.com\/c\/.+ -', testers_message.content)
        message = {'testers_id': str(m_id), "eng_id": str(eng_id), 'card': card.group(0)[-10:-2], 'score': score}
        self.messages.insert_one(message)

    # checks if reaction is legit or poser
    def is_valid_reaction(self, event):
        return event.channel_id in self.config.bug_channels.values() and event.user_id != self.state.me.id

    # listens and adds reactiors to db
    @BasePlugin.listen('MessageReactionAdd')
    def on_reaction(self, event):
        if self.is_valid_reaction(event):
            self.add_reactor(event.channel_id, event.user_id, event.message_id, event.emoji.name)

    # listens, removes reactors from db
    @BasePlugin.listen('MessageReactionRemove')
    def remove_reaction(self, event):
        if self.is_valid_reaction(event):
            user = {'reactor_id': str(event.user_id), 'testers_id': str(event.message_id)}
            self.reactors.find_one_and_delete(user)

    # listens, adds reactions to legit messages
    @BasePlugin.listen('MessageCreate')
    def on_message(self, event):
        if self.validatemessage(event):
            self.addreact(event.message)
