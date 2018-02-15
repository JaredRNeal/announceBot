from disco.bot import Plugin, Config
from disco.bot.command import CommandError

"""
These are all IDs from a test server.
"""

class AnnounceBotConfig(Config):
    #role IDs
    roleIDs = {
        'adminRole': 411674069528870912,
        'android': 411674120196194304,
        'linux': 413477593107660800,
        'ios': 413478048890093579
        }

    channelIDs = {
        'modChannel': 411674296054710273,
        'android': 413446997253554186,
        'iOS': 413447018816733195,
        'desktop': 413447049040756739
    }
