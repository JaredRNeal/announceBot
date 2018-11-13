import os
import signal

from disco.bot import Plugin

from util.GlobalHandlers import command_wrapper, log_to_bot_log


class reload(Plugin):

    @Plugin.command("reload")
    @command_wrapper(perm_lvl=3, log=False)
    def reload_plugins(self, event):
        # do NOT reload this plugin, command execution gets interrupted otherwise!
        todo = [plugin for name, plugin in self.bot.plugins.items() if name != "reload"]
        for p in todo:
            c = p.__class__
            self.bot.rmv_plugin(c)
            self.bot.add_plugin(c)
        event.msg.reply("🔁 All plugins (and configs) have been reloaded")
        log_to_bot_log(self.bot, f"🔁 {event.msg.author} reloaded all plugins (and configs)")


    @Plugin.command("restart")
    @command_wrapper()
    def restart(self, event):
        event.msg.reply("Oh is it that time again? brb")
        # disco doesn't have a build in thing to call for shutting down it seems, using sigkill
        os.kill(os.getpid(), signal.SIGTERM)
