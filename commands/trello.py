from commands.config import AnnounceBotConfig
from commands import BasePlugin
from commands.client import TrelloClient


class TrelloConfig(AnnounceBotConfig):
    trello_key = "TRELLO_KEY_HERE"
    trello_token = "TRELLO_TOKEN_HERE"
    eng_channel = "TBD"
    eng_emoji = ["🤙", "🐸", "🛑", "💯"]
    member_dict = {
        '257932555414667264': '585087294aac3a8562505fe2' # this is just me
    }
    list_dict = {
        # For all, first is NAB, second is CNR, third is claimed fixed
        '57f2a306ca14741151990900': {  # Android
            "🐸": '5b0609fc06bd61f148dc5293',
            "🛑": '58064b37e4c51a85d6d0b68e',
            "💯": '58d178ec961e15df2e742cb7',
            "Verified Bugs": '57fe7f78ddde6b37323bd670'
        },
        '57f2d333b99965a6ba8cd7e0': {  # iOS
            "🐸": '57f2a37248089a5e6a0bf9b6',
            "🛑": '580e8083de3bfbcd4de2ecb9',
            "💯": '57f3de4a5e37d8142fde0313',
            "Verified Bugs": '57fe7f909aa7fe383d56406b'
        },
        '5771673855f47b547f2decc3': {  # Desktop
            "🐸": '580e822c24ce2ffdd624a43c',
            "🛑": '5771678de6092759049c939f',
            "💯": '581286a2c1e6cd4831c862ca',
            "Verified Bugs": '57716787a06d09cf7e0dd1ca'
        },
        '5bc7b4adf7d2b839fa6ac108': {  # Store
            "🐸": '5bce410f7bbb6343675cb496',
            "🛑": '5bf4c065c59169111a5aff6e',
            "💯": '5bce3dcf8098df6e897bc707',
            "Verified Bugs": '5bce483227f80b2351d5f8b8'
        },
    }


@BasePlugin.with_config(TrelloConfig)
class TrelloPlugin(BasePlugin):
    # loads baseplugin and sets up trelloclient
    def load(self, ctx):
        super(TrelloPlugin, self).load(ctx)
        self.messages = self.client.reactions.messages
        self.trello_client = TrelloClient(self.config.trello_key, self.config.trello_token)

    # adds reactions for eng
    def add_eng_reactions(self, message):
        counter = 0
        while counter < 4:
            message.add_reaction(self.config.eng_emoji[counter])
            counter += 1

    # fetches info from db
    def get_message_info(self, message_id):
        msg_info = self.messages.find_one({'eng_id': str(message_id)})
        return msg_info

    # adds member to card in trello
    def assign_member(self, event):
        msg_info = self.get_message_info(str(event.message_id))
        trello_member = self.config.member_dict.get(str(event.user_id))
        if not trello_member:
            return
        self.trello_client.add_member(msg_info.get('card'), trello_member)

    # inverts previous function
    def remove_member(self, event):
        msg_info = self.get_message_info(str(event.message_id))
        trello_member = self.config.member_dict.get(str(event.user_id))
        if not trello_member:
            return
        self.trello_client.remove_member(msg_info.get('card'), trello_member)

    # moves to new list
    def move_list(self, event):
        msg_info = self.get_message_info(event.message_id)
        board = self.trello_client.get_card(msg_info.get('card')).get('idBoard')
        self.trello_client.to_list(msg_info.get('card'), self.config.list_dict.get(board).get(event.emoji.name))

    # moves to verified bugs
    def restore_list(self, event):
        msg_info = self.get_message_info(event.message_id)
        board = self.trello_client.get_card(msg_info.get('card')).get('idBoard')
        self.trello_client.to_list(msg_info.get('card'), self.config.list_dict.get(board).get("Verified Bugs"))

    # listens for message, adds reactions
    @BasePlugin.listen("MessageCreate")
    def on_message(self, event):
        if event.channel.id == self.config.eng_channel:
            self.add_eng_reactions(event)

    # listens for reaction, decides which function to use
    @BasePlugin.listen("MessageReactionAdd")
    def on_reaction(self, event):
        if event.channel_id != self.config.eng_channel or event.user_id == self.state.me.id:
            return
        if event.emoji.name != "🤙":
            self.move_list(event)
        elif event.emoji.name == "🤙":
            self.assign_member(event)

    # listens for reaction removal, decides which function to use
    @BasePlugin.listen("MessageReactionRemove")
    def remove_reaction(self, event):
        if event.channel_id != self.config.eng_channel or event.user_id == self.state.me.id:
            return
        if event.emoji.name != "🤙":
            self.restore_list(event)
        elif event.emoji.name == "🤙":
            self.remove_member(event)
