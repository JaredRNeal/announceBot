from disco.bot.command import CommandLevels

SUPPORTED_SYSTEMS = ['android', 'ios', 'windows', 'linux', 'mac']


def command_level_getter(bot, actor):
    return CommandLevels.TRUSTED
