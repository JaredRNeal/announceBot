from disco.bot import Plugin, Config
from disco.bot.command import CommandError

"""
These are all IDs from a test server.
"""

class AnnounceBotConfig(Config):

    #DTesters role IDs
    """
    admin_Role_IDs = {
        'admin': 197042322939052032,
        'employee': 197042389569765376
    }
    role_IDs = {
        'android': 234838349800538112,
        'bug': 197042209038663680,
        'canary': 351008402052481025,
        'ios': 234838392464998402,
        'linux': 278229255169638410,
        'mac': 351008099978706944,
        'windows': 351008373669494794
        }

    channel_IDs = {
        'android': 411645018105970699,
        'bug': '421790860057903104',
        'canary': 411645098946985984,
        'desktop': 411645098946985984,
        'ios': 411645199866003471,
        'linux': 411645098946985984,
        'mac': 411645098946985984,
        'mod_Channel': 281283303326089216,
        'windows': 411645098946985984
        }
    """
    #Test Server IDs
    #role IDs

    admin_Role_IDs = {
        'employee': 411674069528870912,
        'admin': 416261117845700608
        }

    role_IDs = {
        'android': 411674120196194304,
        'linux': 413477593107660800,
        'ios': 413478048890093579
        }

    channel_IDs = {
        'mod_Channel': 411674296054710273,
        'android': 413446997253554186,
        'iOS': 413447018816733195,
        'desktop': 413447049040756739
        }
