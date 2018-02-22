from disco.bot import Plugin
from disco.api.http import APIException
from disco.api.client import APIClient
from disco.types.guild import GuildMember
from announceBot import AnnounceBotConfig

class EasyAnnouncement(Plugin):

    @Plugin.command('announce', '<role_to_ping:str> [announcement_message:str...]')
    def Make_an_Announcement(self, event, role_to_ping, announcement_message):

        roleName = role_to_ping.lower()
        #make sure it's a valid role name
        if roleName not in AnnounceBotConfig.roleIDs:
            event.msg.reply('Sorry, I cannot find that role')
            return

        #Variables
        Role_as_an_int = AnnounceBotConfig.roleIDs[roleName]
        Role_as_a_string = str(AnnounceBotConfig.roleIDs[roleName])
        IsRoleMentionable = event.guild.roles.get(Role_as_an_int).mentionable
        RoleToMakeMentionable = event.guild.roles.get(Role_as_an_int)
        message_to_announce = "<@&" + Role_as_a_string + "> " + announcement_message
        admin_only_channel = AnnounceBotConfig.channelIDs['modChannel']

        #make sure it's in the right channel
        if event.channel.id != admin_only_channel:
            print("The command was not run in the proper channel")
            return

        #Make sure only an admin can do it TODO Needs to work with employee and admin roles

        if any(AnnounceBotConfig.admin_Role_IDs.values() for role in event.member.roles):

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
