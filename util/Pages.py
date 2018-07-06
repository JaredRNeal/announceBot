import discord

from util import Utils

page_handlers = dict()

known_messages = dict()

prev_emoji = ":gearYes:459697272326848520"
next_emoji = ":gearNo:459697272314265600"


def on_ready():
    load_from_disc()


def register(type, init, update, sender_only=False):
    page_handlers[type] = {
        "init": init,
        "update": update,
        "sender_only": sender_only
    }

def unregister(type_handler):
    if type_handler in page_handlers.keys():
        del page_handlers[type_handler]

def create_new(bot, type, event, **kwargs):
    text, embed, has_pages = page_handlers[type]["init"](event, **kwargs)
    message:discord.Message = event.msg.reply(text, embed=embed)
    data = {
        "type": type,
        "page": 0,
        "trigger": event.msg.id,
        "sender": event.author.id
    }
    for k, v in kwargs.items():
        data[k] = v
    known_messages[str(message.id)] = data

    if has_pages:
        bot.client.api.channels_messages_reactions_create(event.channel.id, message.id, prev_emoji)
        bot.client.api.channels_messages_reactions_create(event.channel.id, message.id, next_emoji)
    if len(known_messages.keys()) > 500:
        del known_messages[list(known_messages.keys())[0]]
    save_to_disc()

def update(message, action, user):
    message_id = str(message.id)
    if message_id in known_messages.keys():
        type = known_messages[message_id]["type"]
        if type in page_handlers.keys():
            data = known_messages[message_id]
            if data["sender"] == user or page_handlers[type]["sender_only"] is False:
                page_num = data["page"]
                text, embed, page = page_handlers[type]["update"](message, page_num, action, data)
                message.edit(content=text, embed=embed)
                known_messages[message_id]["page"] = page
                save_to_disc()
                return True
    return False

def basic_pages(pages, page_num, action):
    if action == "PREV":
        page_num -= 1
    elif action == "NEXT":
        page_num += 1
    if page_num < 0:
        page_num = len(pages) - 1
    if page_num == len(pages):
        page_num = 0
    page = pages[page_num]
    return page, page_num

def save_to_disc():
    Utils.saveToDisk("known_messages", known_messages)

def load_from_disc():
    global known_messages
    known_messages = Utils.fetchFromDisk("known_messages")