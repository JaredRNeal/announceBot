from disco.bot import Plugin
from disco.api.http import APIException
from disco.api.client import APIClient
from disco.types.guild import GuildMember
from announceBot import AnnounceBotConfig

class EasyAnnouncement(Plugin):

    @Plugin.command('announce', parser=True)
    @Plugin.add_argument('roleName', help='Name of role to be pinged')
    @Plugin.add_argument('messageContent', help='The message you actually want to send')

    def checkAdminRole(self, event, args):

        roleName = args.roleName.lower()
        #make sure it's a valid role name
        if roleName not in AnnounceBotConfig.roleIDs:
            event.msg.reply('Sorry, I cannot find that role ID.')
            return

        #Variables
        Role = AnnounceBotConfig.roleIDs[roleName]
        IsRoleMentionable = event.guild.roles.get(Role).mentionable
        RoleToMakeMentionable = event.guild.roles.get(Role)

        #make sure it's in the right channel
        if event.channel.id != AnnounceBotConfig.channelIDs['modChannel']:
            return

        #Make sure only an admin can do it TODO Needs to work with employee and admin roles
        if AnnounceBotConfig.roleIDs['adminRole'] in event.member.roles:
            if IsRoleMentionable == False:
                Role = str(Role)
                RoleToMakeMentionable.update(mentionable=True)
                Channel_to_announce_in = AnnounceBotConfig.channelIDs[args.roleName]
                Channel_to_announce_in = int(Channel_to_announce_in)
                message_to_announce = "<@&" + Role + "> " + args.messageContent
                self.bot.client.api.channels_messages_create(Channel_to_announce_in, message_to_announce)
                RoleToMakeMentionable.update(mentionable=False)
                return

            else:
                RoleToMakeMentionable.update(mentionable=False)
                event.msg.reply("This role was already mentionable. I made it unmentionable, please try again.")
                return
        else:
            event.msg.reply('Sorry, you\'re not allowed to use this command.')
