from commands.config import GitHubConfig
from disco.bot import Plugin
from util.GlobalHandlers import command_wrapper, log_to_bot_log


@Plugin.with_config(GitHubConfig)
class GithubPlugin(Plugin):

    def load(self, ctx):
        super().load(ctx)

    def unload(self, ctx):
        super().unload(ctx)

    @Plugin.command("github", aliases=["source"])
    @command_wrapper(perm_lvl=0, allowed_in_dm=True, allowed_on_server=True)
    def github(self, event):
        event.msg.reply(f"My source code can be found at <{self.config.source_code_location}>")
        log_to_bot_log(self.bot, ":bug: " + str(event.msg.author) + " used the Github command.")
