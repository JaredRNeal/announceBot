from disco.bot import Plugin, Config
from disco.bot.command import CommandError

"""
These are all IDs from a test server.
"""

class AnnounceBotConfig(Config):

    #role IDs
    roleIDs = {
        'adminRole': 197042389569765376,
        'android': 234838349800538112,
        'canary': 351008402052481025,
        'ios': 234838392464998402,
        'linux': 278229255169638410,
        'mac': 351008099978706944,
        'windows': 351008373669494794
        }

    channelIDs = {
        'android': 411645018105970699,
        'canary': 411645098946985984,
        'desktop': 411645098946985984,
        'ios': 411645199866003471,
        'linux': 411645098946985984,
        'mac': 411645098946985984,
        'modChannel': 281283303326089216,
        'windows': 411645098946985984
        }
