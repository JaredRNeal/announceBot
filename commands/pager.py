from disco.bot import Plugin

from util import Pages


class Pager(Plugin):
    def load(self, ctx):
        super(Pager, self).load(ctx)
        Pages.load_from_disc()

    def unload(self, ctx):
        super(Pages, self).unload(ctx)
        Pages.save_to_disc()

    @Plugin.listen("MessageReactionAdd")
    def on_reaction(self, event):
        if event.user_id == self.bot.client.api.users_me_get().id:
            return
        message = self.bot.client.api.channels_messages_get(event.channel_id, event.message_id)
        if event.emoji.name== Pages.prev_emoji:
            if Pages.update(message, "PREV", event.user_id):
                self.bot.client.api.channels_messages_reactions_delete(event.channel_id, event.message_id, Pages.prev_emoji, event.user_id)
        elif event.emoji.name == Pages.next_emoji:
            if Pages.update(message, "NEXT", event.user_id):
                self.bot.client.api.channels_messages_reactions_delete(event.channel_id, event.message_id, Pages.next_emoji, event.user_id)