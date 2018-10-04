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

        if event.user_id == self.bot.client.state.me.id:
            return
        message = self.bot.client.api.channels_messages_get(event.channel_id, event.message_id)
        if event.emoji.name == Pages.prev_emoji:
            Pages.update(message, "PREV", event.user_id)
        elif event.emoji.name == Pages.next_emoji:
            Pages.update(message, "NEXT", event.user_id)

    @Plugin.listen("MessageReactionRemove")
    def on_remove_reaction(self, event):

        self.on_reaction(event)