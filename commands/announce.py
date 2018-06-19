from disco.bot import Plugin
from disco.api.http import APIException
from commands.config import AnnounceBotConfig
import os.path
import json

@Plugin.with_config(AnnounceBotConfig)
class announce(Plugin):
    def load(self, ctx):
        super(announce, self).load(ctx)
        self.event_reported_cards = []
        self.event_total_reports = 0
        self.event_user_reports = dict()
        self.load_event_stats(self.config.event_stats_filename)
    
    def unload(self, ctx):
        self.save_event_stats(self.config.event_stats_filename)
        super(announce, self).unload(ctx)

    @Plugin.command('evilping')
    #just wanted a standard ping command
    def check_bot_heartbeat(self, event):
        if self.checkPerms(event, "mod"):
            event.msg.reply('Evil pong!').after(1).delete()
            self.botlog(event, ":evilDabbit: "+str(event.msg.author)+" used the EvilPing command.")
            event.msg.delete()


    @Plugin.command('announce', '<role_to_ping:str> [announcement_message:str...]')
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

        #Make sure only an admin can do it
        if self.checkPerms(event, "admin"):
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

    @Plugin.command('edit', '<channel_id_to_change>:int> <message_ID_to_edit:int> [edited_announcemented_message:str...]')
    def edit_most_recent_announcement(self, event, channel_id_to_change, message_ID_to_edit, edited_announcemented_message):

        #Variables
        admin_only_channel = self.config.channel_IDs['mod_Channel']

        #verify it's being done in the admin channel
        if event.channel.id != admin_only_channel:
            print("The command was not run in the proper channel")
            return

        #make sure only an admin can use this command and if so, execute
        if any(role in self.config.admin_Role_IDs.values() for role in event.member.roles):
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

        admin_only_channel = self.config.channel_IDs['mod_Channel']
        message_with_multiple_pings = ""
        args.roles = args.roles.lower()
        Channel_to_announce_in = self.config.channel_IDs['desktop']


        #Make sure only an admin can do it
        if self.checkPerms(event, "admin"):
            if event.channel.id != admin_only_channel:
                # make sure it's in the right channel
                event.msg.reply("The command was not run in the proper channel").after(1).delete()
                self.botlog(event, ":deny: "+str(event.msg.author)+" tried to use the Multiping command in the wrong channel.")
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
                    message_to_announce = "<@&" + Role_as_a_string + "> " + args.announcement
                    admin_only_channel = self.config.channel_IDs['mod_Channel']

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
                    self.botlog(event, ":exclamation: "+pingable_role +" was successfully set to unpingable.")


    @Plugin.command('tag', parser=True)
    @Plugin.add_argument('question_title', help="The title of the topic you want to post about.")
    def questions_made_easy(self, event, args):
        #Checks to see if the topic in the list and then replies with the message in annouceBot.py
        args.question_title = args.question_title.lower()
        if self.checkPerms(event, "mod"):
            event.msg.delete()
            if args.question_title in self.config.frequently_asked_questions.keys():
                event.msg.reply(self.config.frequently_asked_questions[args.question_title])
                self.botlog(event, ":notebook: "+str(event.msg.author)+" used the tag command for `"+args.question_title+"`.")

    #Quickly remove the ability for @everyone and Bug Hunters to post in specific channels when some issue is occurring
    @Plugin.command('lockdown', parser=True)
    @Plugin.add_argument('-c', '--channel_names', help="All the channels you want to lock down")
    @Plugin.add_argument('-r', '--reason', help="What's going on thats making you use this command.")
    def emergency_lockdown(self, event, args):
        if self.checkPerms(event, "mod"):
            event.msg.delete()
            for name, channelID in self.config.channels_to_lockdown.items():
                # lock the channel if listed or when locking everything
                if name in args.channel_names or args.channel_names == "all":
                    self.botlog(event, ":lock: The "+name+" channel has been locked by "+str(event.msg.author)+" for the reason: "+args.reason+".")
                    # grab the first (bug hunter or test role) for the queue, grab everyone (or whatever test role is there) for public channels
                    rolenum = 0 if name is "bug" else 1
                    role = event.guild.roles[list(self.config.role_IDs_to_lockdown.values())[rolenum]]
                    channel = event.guild.channels[channelID]
                    channel.send_message(args.reason)
                    # deny reactions and sending perms
                    channel.create_overwrite(role, allow=0, deny=2112)
            event.msg.reply("Lockdown command has successfully completed!")

    # lifting the lockdown
    @Plugin.command('unlock', "<channels:str...>")
    def lift_lockdown(self, event, channels):
        if self.checkPerms(event, "mod"):
            event.msg.delete()
            for name, channelID in self.config.channels_to_lockdown.items():
                # unlock the channel if listed or when unlocking everything
                if name in channels or channels == "all":
                    self.botlog(event, ":unlock: The "+name+" channel has been unlocked by "+str(event.msg.author)+".")
                    # grab the first (bug hunter or test role) for the queue, grab everyone (or whatever test role is there) for public channels
                    rolenum = 0 if name is "bug" else 1
                    role = event.guild.roles[list(self.config.role_IDs_to_lockdown.values())[rolenum]]
                    channel = event.guild.channels[channelID]
                    channel.create_overwrite(role, allow=2048 if name is "bug" else 0, deny=64)
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
    
    @Plugin.command('start', group="event")
    def start_command(self, event):
        """Start the event (author/person to blame when it doesn't work: brxxn)"""

        if event.guild == None:
            return

        # check permissions
        if self.checkPerms(event, "admin"):
            # give bug hunters access to "claimed_fixed" to submit bugs
            bh_role = event.guild.roles[self.config.role_IDs["bug"]]
            submit_channel = event.guild.channels[self.config.event_channel_IDs.get("claimed_fixed")]
            submit_channel.create_overwrite(bh_role, allow=2048, deny=64)
            view_channels = ["ios", "android", "desktop", "linux"]

            for name in view_channels:
                channel = event.guild.roles[self.config.event_channel_IDs.get(name)]
                if channel == None:
                    continue
                channel.create_overwrite(bh_role, allow=0, deny=2112) # deny: send messages, add reactions
                channel.create_overwrite(bh_role, allow=66560, deny=0) # allow: read messages, read message history

            event.channel.send(":ok_hand: unlocked event channels to bug hunters.")
            self.botlog(event, ":unlock: {name} (id: {id}) started an event.".format(name=str(event.msg.author), id=event.msg.author.id))
    
    @Plugin.command('submit', '<bug_type:str> <link:str> <message:str...>', group="event")
    def submit_command(self, event, bug_type, link, message):
        """Event submission command (author/person to blame when it doesn't work: brxxn)"""

        # make sure there is a guild
        if event.guild == None:
            return

        # delete the message
        event.msg.delete()

        # make sure user posted in submit channel
        submit_channel = self.config.event_channel_IDs["claimed_fixed"]
        if event.channel.id != submit_channel:
            event.channel.send_message("command cannot be run in this channel.").after(3).delete()
            return

        # make sure vaild type
        bug_type = bug_type.lower()
        vaild_types = ["ios", "android", "desktop", "linux"]
        if bug_type not in vaild_types:
            event.channel.send_message("invalid bug type. valid types include: `ios, android, desktop, linux`").after(3).delete()
            return

        # verify link
        if not link.lower().startswith("https://trello.com/c/"):
            event.channel.send_message("please make sure your message starts with `https://trello.com/c/`").after(3).delete()
            return
        if len(link) <= 21:
            event.channel.send_message("please include a valid trello url").after(3).delete()
            return

        # check to see if it's already reported
        card_id = link.split("https://trello.com/c/")[1].split("/")[0]
        if card_id in self.event_reported_cards:
            event.channel.send_message("already reported. next time, please use search to find if a bug has already been reported.").after(6).delete()
            return

        # submit the bug
        report_channel = self.config.event_channel_IDs[bug_type]
        event.guild.channels[report_channel].send_message("{name} (`{id}`) reported {a_or_an} {bug_type} bug: `{message}`, {link}".format(
            name=str(event.msg.author),
            id=str(event.msg.author.id),
            a_or_an="an" if bug_type == "ios" or bug_type == "android" else "a",
            bug_type=bug_type,
            message=message,
            link=link
        ))

        # alert the user
        event.channel.send_message(":ok_hand: successfully reported bug.").after(2).delete()

        # add to statistics
        current_user_reports = self.event_user_reports.setdefault(event.msg.author.id, 0)

        self.event_reported_cards.append(card_id)
        self.event_total_reports = self.event_total_reports + 1
        self.event_user_reports[event.msg.author.id] = current_user_reports + 1

        # report announcement to botlog: 50, 100, 200, 300, 400...
        announce_report_to_botlog = self.event_total_reports % 100 == 0 or self.event_total_reports == 50
        if announce_report_to_botlog and self.event_total_reports != 0:
            self.botlog(event, ":crown: reached {report} total reports in current trello cleaning event".format(report=str(self.event_total_reports)))
            return

        # save reports
        if self.event_total_reports % 50 == 0 and self.event_total_reports != 0:
            self.save_event_stats(self.config.event_stats_filename)
    
    @Plugin.command('winners', group="event")
    def event_winners(self, event):
        """Find 1st-10th winners in bug reporting (author/person to blame when it doesn't work: brxxn)"""
        # check guild
        if event.guild == None:
            return

        if not self.checkPerms(event, "mod"):
            return

        message = "Estimated winners are:\n\n"

        # sort from largest to smallest reports
        count = 0

        for winner_id, reports in sorted(self.event_user_reports.items(), key=lambda x: x[1], reverse=True):
            count = count + 1
            line = "{count}: <@{id}> ({reports} reports)\n".format(count=str(count), name=str(event.guild.members[winner_id]), reports=str(reports), id=str(winner_id))
            message = message + line
            # stop at 10
            if count == 10:
                break

        message = message + "\nThanks for participating in the Trello Cleaning Event! Note that these scores are not final, as not all reports have been approved yet."
        event.msg.delete()
        event.channel.send_message(message)
    
    @Plugin.command('end', group="event")
    def end_event(self, event):
        """End the event (author/person to blame when it doesn't work: brxxn)"""
        # check guild
        if event.guild == None:
            return
        
        if self.checkPerms(event, "admin"):
            bh_role = event.guild.roles[self.config.role_IDs["bug"]]
            lock_channels = ["ios", "android", "desktop", "linux", "claimed_fixed"]
            for i in lock_channels:
                channel = event.guild.channels[self.config.event_channel_IDs[i]]
                # allow: none; deny: view channel, send message, add reactions
                channel.create_overwrite(bh_role, allow=0, deny=2112)
            event.msg.delete()
            event.channel.send_message(":ok_hand: event ended - channels locked. note that statistics have **not** been reset.").after(5).delete()
            self.botlog(event, ":lock: {user} ended event (locked all event channels)".format(user=str(event.msg.author)))
    
    @Plugin.command('clearall', group="event")
    def clear_stats(self, event):
        """Clear all statistics (author/person to blame when it doesn't work: brxxn)"""
        # check guild
        if event.guild == None:
            return
        
        # check perms
        if self.checkPerms(event, "admin"):
            # clear
            self.event_reported_cards = []
            self.event_total_reports = 0
            self.event_user_reports.clear()

            event.msg.delete()
            event.channel.send_message(":ok_hand: all statistics cleared.").after(5).delete()
            self.botlog(event, ":wastebasket: {user} cleared all statistics for the event".format(user=str(event.msg.author)))
    
    @Plugin.command('clearuser', "<user:snowflake> <reason:str...>", group="event")
    def clear_user(self, event, user, reason):
        """Clear user statistics (author/person to blame when it doesn't work: brxxn)"""
        # check guild
        if event.guild == None:
            return
        
        # check perms
        if self.checkPerms(event, "mod"):
            event.msg.delete()
            # check user
            if self.event_user_reports.get(user, None) == None:
                event.channel.send_message("failed to clear stats: user doesn't have any statistics.").after(5).delete()
                return
            # clear report stats from user
            user_reports = self.event_user_reports[user]
            self.event_user_reports[user] = 0
            # clear report stats from global
            if self.event_total_reports - user_reports < 0:
                event.channel.send_message("failed to clear stats: user stats cleared, but global couldn't be cleared. tell dabbit if this happens.").after(6).delete()
                self.botlog(event, ":wastebasket: {mod} cleared stats for user {user} with reason {reason} (but it failed to update globally)".format(mod=str(event.msg.author), user=str(user), reason=reason))
                return
            self.event_total_reports = self.event_total_reports - user_reports
            # inform user and bot log
            event.channel.send_message(":ok_hand: cleared reports from user.").after(4).delete()
            self.botlog(event, ":wastebasket: {mod} cleared stats for user {user} with reason {reason}".format(mod=str(event.msg.author), user=str(user), reason=reason))
    
    @Plugin.command('addreports', '<user:snowflake> <amount:int>', group="event")
    def add_reports(self, event, user, amount):
        """Add reports to user if the bot went offline. (author/person to blame when it doesn't work: brxxn)"""
        # check guild
        if event.guild == None:
            return
        
        # check perms
        if self.checkPerms(event, "mod"):
            # delete message
            event.msg.delete()

            # check amount
            if amount <= 0:
                event.channel.send_message("amount must be more than 0.").after(5).delete()
                return

            # add to user
            current_reports = self.event_user_reports.setdefault(user, 0)
            updated_reports = current_reports + amount
            self.event_user_reports[user] = updated_reports

            # add to global
            self.event_total_reports = self.event_total_reports + amount

            # notify author and bot log
            event.channel.send_message(":ok_hand: updated report count for user.").after(5).delete()
            self.botlog(event, ":newspaper: {user} given {amount} reports by {author}".format(user=str(user), amount=str(amount), author=str(event.msg.author.id)))

    def save_event_stats(self, filename):
        try:
            f = open(filename, "w")
            save_dict = {
                "event_reported_cards": self.event_reported_cards,
                "event_total_reports": self.event_total_reports,
                "event_user_reports": self.event_user_reports
            }
            f.write(json.dumps(save_dict))
            f.close()
        except IOError as ex:
            print("failed to open file: {file}\nstrerror: {strerror}".format(file=filename, strerror=ex.strerror))
    
    def load_event_stats(self, filename):
        if not os.path.isfile(filename):
            return
        try:
            f = open(filename, "r")
            event_stats = f.read()
            event_stats_parsed = json.loads(event_stats)
            self.event_reported_cards = event_stats_parsed.get("event_reported_cards", [])
            self.event_total_reports = event_stats_parsed.get("event_total_reports", 0)
            self.event_user_reports = event_stats_parsed.get("event_user_reports", dict())
        except IOError as ex:
            print("failed to open file: {file}\nstrerror: {strerror}".format(file=filename, strerror=ex.strerror))

    def checkPerms(self, event, type):
        # get roles from the config
        roles = getattr(self.config, str(type)+'_roles').values()
        if any(role in roles for role in event.member.roles):
            return True
        event.msg.reply(":lock: You do not have permission to use this command!")
        self.botlog(event, ":warning: "+str(event.msg.author)+" tried to use a command they do not have permission to use.")
        return False

    def botlog(self, event, message):
        channel = event.guild.channels[self.config.channel_IDs['bot_log']]
        channel.send_message(message)
