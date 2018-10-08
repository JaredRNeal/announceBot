import traceback
from datetime import datetime

from disco.types.message import MessageEmbed
from disco.util import sanitize

from util import Utils

LOADED = False
INFO = None

# perm lvls:
# 0: public
# 1: bug-hunter
# 2: mod+
# 3: admin

def is_public(member):
    return True

def is_hunter(member):
    return has_role(member, [INFO["HUNTER_ROLE"]]) or is_mod(member)

def is_mod(member):
    return has_role(member, INFO["MOD_ROLES"]) or is_admin(member)

def is_admin(member):
    return has_role(member, INFO["ADMIN_ROLES"])

def has_role(member, roles):
    return any(role in roles for role in member.roles)

PERM_CHECKS = [
    is_public,
    is_hunter,
    is_mod,
    is_admin
]

#this handles all the command wrapping, with some defaults
def command_wrapper(perm_lvl = 2, log=True, allowed_on_server = True, allowed_in_dm = False):
    def func_receiver(func):
        def func_wrapper(*args, **kwargs):
            if not LOADED:
                load()
            #extract event param
            plugin = args[0]
            event = args[1]
            #grab user from guild and validate permissions (this assumes the user is on there, but since the bot is not used anywhere else this is a safe assumption to make)
            member = plugin.bot.client.api.guilds_members_get(INFO["SERVER_ID"], event.msg.author.id)
            allowed = PERM_CHECKS[perm_lvl](member)
            if not allowed:
                log_to_bot_log(plugin.bot, f":warning: {event.msg.author} (``{event.msg.author.id}``) tried to use a command they do not have permission to use: ``{sanitize.S(event.msg.content, escape_codeblocks=True)} ``")
                event.msg.reply(":lock: You do not have permission to use this command!").after(10).delete()
                event.msg.delete()
            else:
                #can we execute here?
                if (event.guild is not None and allowed_on_server) or (event.guild is None and allowed_in_dm):
                    try:
                        func(*args, **kwargs)
                    except Exception as exception:
                        handle_exception(event, plugin.bot, exception)
                    else:
                        if log:
                            log_to_bot_log(plugin.bot, f":wrench: {event.msg.author} executed a command: {sanitize.S(event.msg.content, escape_codeblocks=True)}")
        return func_wrapper
    return func_receiver

def handle_exception(event, bot, exception):
    # catch everything and extract all info we can from the func arguments so we see what exactly was going on
    print("Exception caught, extracting information")

    print("====EXCEPTION====")
    print(exception)

    print("====STACKTRACE====")
    print(traceback.format_exc())

    print("====ORIGINAL MESSAGE====")
    print(event.msg.content)

    print("====SENDER====")
    print(event.msg.author)

    print("====Channel====")
    print("{} ({})".format(event.msg.channel.name, event.msg.channel.id))

    embed = MessageEmbed()
    embed.title = "Exception caught"
    embed.add_field(name="Original message", value=str(event.msg.content))
    embed.add_field(name="Channel", value="{} ({})".format(event.msg.channel.name, event.msg.channel.id))
    embed.add_field(name="Sender", value=str(event.msg.author))
    embed.add_field(name="Exception", value=str(exception))
    embed.add_field(name="Stacktrace", value=str(traceback.format_exc()))
    embed.timestamp = datetime.utcnow().isoformat()
    embed.color = int('ff0000', 16)
    log_to_bot_log(bot, embed=embed)

def log_to_bot_log(bot, *args, **kwargs):
    if not LOADED:
        load()
    bot.client.state.guilds[INFO["SERVER_ID"]].channels[INFO["LOG_CHANNEL"]].send_message(*args, **kwargs)

def load():
    global LOADED, INFO
    INFO = Utils.fetchFromDisk("config/global")
    LOADED = True
