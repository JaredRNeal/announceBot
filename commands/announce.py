from disco.bot import Plugin
from disco.api.http import APIException
from disco.api.client import APIClient
from disco.types.guild import GuildMember
from disco.types.message import MessageEmbed
from datetime import datetime
from announceBot import AnnounceBotConfig
from announceBot import FAQtopics



class EasyAnnouncement(Plugin):

    @Plugin.command('evilping')
    #just wanted a standard ping command
    def check_bot_heartbeat(self, event):
        event.msg.reply('Evil pong!').after(10).delete()
        event.msg.delete()

    @Plugin.command('announce', '<role_to_ping:str> [announcement_message:str...]')
    def Make_an_Announcement(self, event, role_to_ping, announcement_message):

        role_Name = role_to_ping.lower()
        #make sure it's a valid role name
        if role_Name not in AnnounceBotConfig.role_IDs:
            event.msg.reply('Sorry, I cannot find the role `'+role_Name+'`')
            return

        #Variables
        Role_as_an_int = AnnounceBotConfig.role_IDs[role_Name]
        Role_as_a_string = str(AnnounceBotConfig.role_IDs[role_Name])
        Is_Role_Mentionable = event.guild.roles.get(Role_as_an_int).mentionable
        Role_To_Make_Mentionable = event.guild.roles.get(Role_as_an_int)
        message_to_announce = "<@&" + Role_as_a_string + "> " + announcement_message
        admin_only_channel = AnnounceBotConfig.channel_IDs['mod_Channel']

        #make sure it's in the right channel
        if event.channel.id != admin_only_channel:
            print("The command was not run in the proper channel")
            return

        #Make sure only an admin can do it
        if any(role in AnnounceBotConfig.admin_Role_IDs.values() for role in event.member.roles):

            if Is_Role_Mentionable == False:
                role_Name = str(role_Name)
                Channel_to_announce_in = AnnounceBotConfig.channel_IDs[role_Name]
                Channel_to_announce_in = int(Channel_to_announce_in)
                Role_To_Make_Mentionable.update(mentionable=True)
                self.bot.client.api.channels_messages_create(Channel_to_announce_in, message_to_announce)
                Role_To_Make_Mentionable.update(mentionable=False)
                return

            else:
                Role_To_Make_Mentionable.update(mentionable=False)
                event.msg.reply("This role was already mentionable. I made it unmentionable, please try again.")
                return
        else:
            event.msg.reply('Sorry, you\'re not allowed to use this command.')

    @Plugin.command('edit', '<channel_id_to_change>:int> <message_ID_to_edit:int> [edited_announcemented_message:str...]')
    def edit_most_recent_announcement(self, event, channel_id_to_change, message_ID_to_edit, edited_announcemented_message):

        #Variables
        admin_only_channel = AnnounceBotConfig.channel_IDs['mod_Channel']

        #verify it's being done in the admin channel
        if event.channel.id != admin_only_channel:
            print("The command was not run in the proper channel")
            return

        #make sure only an admin can use this command and if so, execute
        if any(role in AnnounceBotConfig.admin_Role_IDs.values() for role in event.member.roles):
            try:
                self.client.api.channels_messages_modify(channel=channel_id_to_change, message=message_ID_to_edit, content=edited_announcemented_message)
                event.msg.reply('I have successfully changed the messaged the message you told me to.')

            except APIException:
                event.msg.reply('I can\'t find a message with that ID in a channel with that ID. Please double check that you put the IDs in the correct order. It has to be `!edit <channel ID> <message ID> new message`')

        else:
            print('The user who tried to use this command does not have the appropriate role.')
            return


    #Hopefully clear from the command name, but this command allows you to ping and announce to multiple DESKTOP roles simultaneously.
    @Plugin.command('multiping', parser=True)
    @Plugin.add_argument('-r', '--roles', help="all of the roles you want to ping")
    @Plugin.add_argument('-a', '--announcement', help="the message you want to send out to everyone.")
    def ping_multiple_roles(self, event, args):

        admin_only_channel = AnnounceBotConfig.channel_IDs['mod_Channel']
        message_with_multiple_pings = ""
        args.roles = args.roles.lower()
        Channel_to_announce_in = AnnounceBotConfig.channel_IDs['desktop']

        #make sure it's in the right channel
        if event.channel.id != admin_only_channel:
            print("The command was not run in the proper channel")
            return

        #Make sure only an admin can do it
        if any(role in AnnounceBotConfig.admin_Role_IDs.values() for role in event.member.roles):

            if "ios" in args.roles or "android" in args.roles:
                event.msg.reply("This command can only be used for desktop roles. Linux, Windows, Mac and Canary.")
                return

            for pingable_role in AnnounceBotConfig.role_IDs.keys():
                if pingable_role in args.roles:
                    #Variables

                    Role_as_an_int = AnnounceBotConfig.role_IDs[pingable_role]
                    Role_as_a_string = str(AnnounceBotConfig.role_IDs[pingable_role])
                    Is_Role_Mentionable = event.guild.roles.get(Role_as_an_int).mentionable
                    Role_To_Make_Mentionable = event.guild.roles.get(Role_as_an_int)
                    message_to_announce = "<@&" + Role_as_a_string + "> " + args.announcement
                    admin_only_channel = AnnounceBotConfig.channel_IDs['mod_Channel']

                    if Is_Role_Mentionable == False:
                        Role_To_Make_Mentionable.update(mentionable=True)
                    message_with_multiple_pings = message_with_multiple_pings + "<@&" + Role_as_a_string + "> "

            if message_with_multiple_pings == "":
                event.msg.reply("Something strange happened. Please let Dabbit know and try again.")
                return
            else:
                message_with_multiple_pings = message_with_multiple_pings + args.announcement
                self.bot.client.api.channels_messages_create(Channel_to_announce_in, message_with_multiple_pings)

            for pingable_role in AnnounceBotConfig.role_IDs.keys():

                #Variables
                Role_To_Make_Unmentionable = event.guild.roles.get(AnnounceBotConfig.role_IDs[pingable_role])

                if Is_Role_Mentionable == True:
                    Role_To_Make_Unmentionable.update(mentionable=False)
                    print (pingable_role +" was successfully set to unpingable.")

        else:
            print("The user that attempted to use the Multiping command does not have the proper permissions so the command was ignored.")
            return


    @Plugin.command('tag', parser=True)
    @Plugin.add_argument('question_title', help="The title of the topic you want to post about.")
    def questions_made_easy(self, event, args):
        #Checks to see if the topic in the list and then replies with the message in annouceBot.py
        args.question_title = args.question_title.lower()
        if any(role in AnnounceBotConfig.mod_role.values() for role in event.member.roles):
            event.msg.delete()
            if args.question_title in FAQtopics.frequently_asked_questions.keys():
                event.msg.reply(FAQtopics.frequently_asked_questions[args.question_title])
        else:
            print("User does not have the correct permissions to use this command.")
            return





        #hello world
