from disco.api.http import APIException
from disco.bot import Plugin
from disco.types.guild import VerificationLevel

from commands.config import AnnounceBotConfig
from util.GlobalHandlers import command_wrapper, log_to_bot_log


@Plugin.with_config(AnnounceBotConfig)
class announce(Plugin):
    def load(self, ctx):
        super(announce, self).load(ctx)

    def unload(self, ctx):
        super(announce, self).unload(ctx)

    # just wanted a standard ping command
    @Plugin.command('evilping')
    @command_wrapper(log=False)
    def check_bot_heartbeat(self, event):
        event.msg.reply('Evil pong!').after(1).delete()
        log_to_bot_log(self.bot, ":evilDabbit: "+str(event.msg.author)+" used the EvilPing command.")
        event.msg.delete()

    @Plugin.command('employee', "<new_employee:str>")
    def make_employee(self, event, new_employee):
        if any(role == 197042389569765376  for role in event.member.roles):
            if new_employee.startswith("<@"):
                id = new_employee[2:-1]
            elif new_employee.startswith("<@!"):
                id = new_employee[3:-1]
            else:
                id = new_employee
            try:
                id = int(id)
            except Exception:
                event.msg.reply("Unable to parse that as mention or ID")
            else:
                if id in event.guild.members.keys():
                    self.bot.client.api.guilds_members_roles_add(event.guild.id, id, 197042389569765376 )
                    event.msg.reply("Role added")
                else:
                    event.msg.reply("Unable to find that person")
        else:
            event.msg.reply(":lock: You do not have permission to use this command!")
            log_to_bot_log(self.bot, ":warning: {} tried to use a command they do not have permission to use.".format(str(event.msg.author)))




    @Plugin.command('announce', '<role_to_ping:str> [announcement_message:str...]')
    @command_wrapper(perm_lvl=2)
    def Make_an_Announcement(self, event, role_to_ping, announcement_message):

        role_Name = role_to_ping.lower()
        #make sure it's a valid role name
        if role_Name not in self.config.role_IDs:
            event.msg.reply('Sorry, I cannot find the role `'+role_Name+'`')
            return

        #Variables
        Role_as_an_int = self.config.role_IDs[role_Name]
        Role_as_a_string = str(self.config.role_IDs[role_Name])
        Is_Role_Mentionable = event.guild.roles.get(Role_as_an_int).mentionable
        Role_To_Make_Mentionable = event.guild.roles.get(Role_as_an_int)
        message_to_announce = "<@&" + Role_as_a_string + "> " + announcement_message
        admin_only_channel = self.config.channel_IDs['mod_Channel']

        # make sure it's in the right channel
        if event.channel.id != admin_only_channel:
            print("The command was not run in the proper channel")
            return

        if Is_Role_Mentionable == False:
            role_Name = str(role_Name)
            Channel_to_announce_in = self.config.channel_IDs[role_Name]
            Channel_to_announce_in = int(Channel_to_announce_in)
            Role_To_Make_Mentionable.update(mentionable=True)
            self.bot.client.api.channels_messages_create(Channel_to_announce_in, message_to_announce)
            Role_To_Make_Mentionable.update(mentionable=False)
            return

        else:
            Role_To_Make_Mentionable.update(mentionable=False)
            event.msg.reply("This role was already mentionable. I made it unmentionable, please try again.")
            return

    @Plugin.command('update', '<channel_id_to_change>:int> <message_ID_to_edit:int> [edited_announcemented_message:str...]')
    @command_wrapper(perm_lvl=2)
    def edit_most_recent_announcement(self, event, channel_id_to_change, message_ID_to_edit, edited_announcemented_message):

        #Variables
        admin_only_channel = self.config.channel_IDs['mod_Channel']

        #verify it's being done in the admin channel
        if event.channel.id != admin_only_channel:
            print("The command was not run in the proper channel")
            return

        #make sure only an admin can use this command and if so, execute
        try:
            self.client.api.channels_messages_modify(channel=channel_id_to_change, message=message_ID_to_edit, content=edited_announcemented_message)
            event.msg.reply('I have successfully changed the messaged the message you told me to.')

        except APIException:
            event.msg.reply('I can\'t find a message with that ID in a channel with that ID. Please double check that you put the IDs in the correct order. It has to be `!edit <channel ID> <message ID> new message`')


    #Hopefully clear from the command name, but this command allows you to ping and announce to multiple DESKTOP roles simultaneously.
    @Plugin.command('multiping', parser=True)
    @Plugin.add_argument('-r', '--roles', help="all of the roles you want to ping")
    @Plugin.add_argument('-a', '--announcement', help="the message you want to send out to everyone.")
    @command_wrapper(perm_lvl=2)
    def ping_multiple_roles(self, event, args):

        admin_only_channel = self.config.channel_IDs['mod_Channel']
        message_with_multiple_pings = ""
        args.roles = args.roles.lower()
        Channel_to_announce_in = self.config.channel_IDs['desktop']


        if event.channel.id != admin_only_channel:
            # make sure it's in the right channel
            event.msg.reply("The command was not run in the proper channel").after(1).delete()
            log_to_bot_log(self.bot, ":deny: "+str(event.msg.author)+" tried to use the Multiping command in the wrong channel.")
            return
        if "ios" in args.roles or "android" in args.roles:
            event.msg.reply("This command can only be used for desktop roles. Linux, Windows, Mac and Canary.")
            return
        for pingable_role in self.config.role_IDs.keys():
            if pingable_role in args.roles:
                #Variables
                Role_as_an_int = self.config.role_IDs[pingable_role]
                Role_as_a_string = str(self.config.role_IDs[pingable_role])
                Is_Role_Mentionable = event.guild.roles.get(Role_as_an_int).mentionable
                Role_To_Make_Mentionable = event.guild.roles.get(Role_as_an_int)

                if Is_Role_Mentionable == False:
                    Role_To_Make_Mentionable.update(mentionable=True)
                message_with_multiple_pings = message_with_multiple_pings + "<@&" + Role_as_a_string + "> "
        if message_with_multiple_pings == "":
            event.msg.reply("Something strange happened. Please let Dabbit know and try again.")
            return
        else:
            message_with_multiple_pings = message_with_multiple_pings + args.announcement
            self.bot.client.api.channels_messages_create(Channel_to_announce_in, message_with_multiple_pings)
        for pingable_role in self.config.role_IDs.keys():
            #Variables
            Role_To_Make_Unmentionable = event.guild.roles.get(self.config.role_IDs[pingable_role])
            if Is_Role_Mentionable == True:
                Role_To_Make_Unmentionable.update(mentionable=False)
                log_to_bot_log(self.bot, ":exclamation: "+pingable_role +" was successfully set to unpingable.")


    @Plugin.command('tag', parser=True)
    @Plugin.add_argument('question_title', help="The title of the topic you want to post about.")
    @command_wrapper(log=False)
    def questions_made_easy(self, event, args):
        #Checks to see if the topic in the list and then replies with the message in annouceBot.py
        args.question_title = args.question_title.lower()
        event.msg.delete()
        if args.question_title in self.config.frequently_asked_questions.keys():
            event.msg.reply(self.config.frequently_asked_questions[args.question_title])
            log_to_bot_log(self.bot, ":notebook: "+str(event.msg.author)+" used the tag command for `"+args.question_title+"`.")

    #Quickly remove the ability for @everyone and Bug Hunters to post in specific channels when some issue is occurring
    @Plugin.command('lockdown', parser=True)
    @Plugin.add_argument('-c', '--channel_names', help="All the channels you want to lock down")
    @Plugin.add_argument('-r', '--reason', help="What's going on thats making you use this command.")
    @command_wrapper(log=False)
    def emergency_lockdown(self, event, args):
        event.msg.delete()
        for name, channelID in self.config.channels_to_lockdown.items():
            # lock the channel if listed or when locking everything
            if name in args.channel_names or args.channel_names == "all":
                log_to_bot_log(self.bot, ":lock: The "+name+" channel has been locked by "+str(event.msg.author)+" for the reason: "+args.reason+".")
                # grab the first (bug hunter or test role) for the queue, grab everyone (or whatever test role is there) for public channels
                rolename = "bug_hunter" if name == "bug" else "everyone"
                role = event.guild.roles[self.config.role_IDs_to_lockdown[rolename]]
                channel = event.guild.channels[channelID]
                channel.send_message(args.reason)
                # deny reactions and sending perms
                channel.create_overwrite(role, allow=0, deny=2112)
        event.msg.reply("Lockdown command has successfully completed!")

    # lifting the lockdown
    @Plugin.command('unlock', "<channels:str...>")
    @command_wrapper()
    def lift_lockdown(self, event, channels):
        event.msg.delete()
        for name, channelID in self.config.channels_to_lockdown.items():
            # unlock the channel if listed or when unlocking everything
            if name in channels or channels == "all":
                log_to_bot_log(self.bot, ":unlock: The "+name+" channel has been unlocked by "+str(event.msg.author)+".")
                # grab the first (bug hunter or test role) for the queue, grab everyone (or whatever test role is there) for public channels
                rolename = "bug_hunter" if name == "bug" else "everyone"
                role = event.guild.roles[self.config.role_IDs_to_lockdown[rolename]]
                channel = event.guild.channels[channelID]
                channel.create_overwrite(role, allow=2048 if name == "bug" else 0, deny=64)
                # clean up lockdown message, scan last 5 messages just in case
                limit = 5
                count = 0
                for message in channel.messages_iter(chunk_size=limit):
                    if message.author.id == self.bot.client.api.users_me_get().id:
                        message.delete()
                    count = count + 1
                    if count >= limit:
                        break
        event.msg.reply("Unlock command has successfully completed!")

    @Plugin.command('verification', '<level:str> [reason:str...]')
    @command_wrapper()
    def change_verification_level(self, event, level, reason=None):
        vl = VerificationLevel.get(level.lower())
        if vl is not None:
            if event.guild.verification_level != vl:
                try:
                    self.bot.client.api.guilds_modify(event.guild.id, reason, verification_level=vl.value)
                except APIException:
                    event.msg.reply("Failed to change the server verification level")
                else:
                    if reason is None:
                        reason = ""
                    else:
                        reason = " with reason `{}`".format(reason)
                    log_to_bot_log(self.bot, ":vertical_traffic_light: {} changed the server verification level to {}{}".format(event.msg.author, level, reason))
                    event.msg.reply("Server verification level changed successfully")
            else:
                event.msg.reply("The server verification level is already set to {}".format(level))
        else:
            event.msg.reply("That level name doesn't seem to be valid")

    @Plugin.command('a11y')
    def grant_role(self, event):
        if 441739649753546764 in event.member.roles:
            event.member.remove_role(441739649753546764)
            log_to_bot_log(self.bot, ":thumbsdown: <@" +str(event.author.id)+ "> removed the A11y role from themselves.")
            event.msg.reply("<@" +str(event.author.id)+ "> I have removed the A11y (Accessibility Role) from you. Use the same command again to add the role to yourself.").after(5).delete()
            event.msg.delete()
        else:
            event.member.add_role(441739649753546764)
            log_to_bot_log(self.bot, ":thumbsup: <@" +str(event.author.id)+ "> added the A11y role to themselves.")
            event.msg.reply("<@" +str(event.author.id)+ "> I have added the A11y (Accessibility Role) to you. Use the same command again to remove the role from yourself.").after(5).delete()
            event.msg.delete()