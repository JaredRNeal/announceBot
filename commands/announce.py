from disco.bot import Plugin
from disco.api.http import APIException
from disco.api.client import APIClient
from disco.types.guild import GuildMember
from announceBot import AnnounceBotConfig

class EasyAnnouncement(Plugin):

    @Plugin.command('announce', parser=True)
    @Plugin.add_argument('roleName', help='Name of role to be pinged')
    #TODO figure out how to make it so the messageContent doesn't break with quotes
    @Plugin.add_argument('messageContent', help='The message you actually want to send')

    def Make_an_Announcement(self, event, args):

        roleName = args.roleName.lower()
        #make sure it's a valid role name
        if roleName not in AnnounceBotConfig.roleIDs:
            event.msg.reply('Sorry, I cannot find that role')
            return

        #Variables
        Role_as_an_int = AnnounceBotConfig.roleIDs[roleName]
        Role_as_a_string = str(AnnounceBotConfig.roleIDs[roleName])
        IsRoleMentionable = event.guild.roles.get(Role_as_an_int).mentionable
        RoleToMakeMentionable = event.guild.roles.get(Role_as_an_int)
        message_to_announce = "<@&" + Role_as_a_string + "> " + args.messageContent
        admin_only_channel = AnnounceBotConfig.channelIDs['modChannel']

        #make sure it's in the right channel
        if event.channel.id != admin_only_channel:
            print("The command was not run in the proper channel")
            return

        #Make sure only an admin can do it TODO Needs to work with employee and admin roles

        try:
            if AnnounceBotConfig.roleIDs['adminRole'] in event.member.roles:

                if IsRoleMentionable == False:
                    roleName = str(roleName)
                    Channel_to_announce_in = AnnounceBotConfig.channelIDs[roleName]
                    Channel_to_announce_in = int(Channel_to_announce_in)
                    RoleToMakeMentionable.update(mentionable=True)
                    self.bot.client.api.channels_messages_create(Channel_to_announce_in, message_to_announce)
                    RoleToMakeMentionable.update(mentionable=False)
                    return

                else:
                    RoleToMakeMentionable.update(mentionable=False)
                    event.msg.reply("This role was already mentionable. I made it unmentionable, please try again.")
                    return
            else:
                event.msg.reply('Sorry, you\'re not allowed to use this command.')
        except:
            print("Some error happened. Making sure the role is still not mentionable")
            if IsRoleMentionable == True:
                RoleToMakeMentionable.update(mentionable=False)
                return
