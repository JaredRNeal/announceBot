from disco.bot import Plugin
from commands.config import EventsPluginConfig
import os.path
import json
import shutil

@Plugin.with_config(EventsPluginConfig)
class Events(Plugin):

    def load(self, ctx):
        super(Events, self).load(ctx)
        self.event_reported_cards = []
        self.event_pending_reports = []
        self.event_approved_reports = []
        self.event_denied_reports = []
        self.load_event_stats(self.config.event_stats_filename)
    
    def unload(self, ctx):
        self.save_event_stats(self.config.event_stats_filename)
        super(Events, self).unload(ctx)
    
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
        report_message = event.guild.channels[report_channel].send_message("{name} (`{id}`) reported {a_or_an} {bug_type} bug: `{message}`, {link}".format(
            name=str(event.msg.author),
            id=str(event.msg.author.id),
            a_or_an="an" if bug_type == "ios" or bug_type == "android" else "a",
            bug_type=bug_type,
            message=message,
            link=link
        ))

        report_message.react(event.guild.emojis[self.config.emojis.green_tick])
        report_message.react(event.guild.emojis[self.config.emojis.red_tick])

        # alert the user
        event.channel.send_message(":ok_hand: successfully reported bug.").after(2).delete()

        # add to statistics

        self.event_reported_cards.append(card_id)
        self.event_pending_reports[event.msg.author.id] = self.event_pending_reports.append({
            "name": str(event.msg.author),
            "author_id": str(event.msg.author.id),
            "category": bug_type,
            "message": message,
            "card_id": card_id,
            "message_id": report_message.id,
            "approved": False
        })

        # report announcement to botlog: 50, 100, 200, 300, 400...
        announce_report_to_botlog = self.get_total_reports() % 100 == 0 or self.get_total_reports() == 50
        if announce_report_to_botlog and self.get_total_reports() != 0:
            self.botlog(event, ":crown: reached {report} total reports in current trello cleaning event".format(report=str(self.get_total_reports())))
            return

        # save reports
        if self.get_total_reports() % 100 == 0 and self.get_total_reports() != 0:
            self.save_event_stats(self.config.event_stats_filename)
    
    @Plugin.command('winners', group="event")
    def event_winners(self, event):
        """Find 1st-10th winners in bug reporting (author/person to blame when it doesn't work: brxxn)"""
        # check guild
        if event.guild == None:
            return

        if not self.checkPerms(event, "admin"):
            return

        message = "Total amount of approved reports: {total_amount}\nWinners are:\n\n".format(total_amount=str(self.get_approved_reports()))

        # sort from largest to smallest reports
        count = 0
        # build list of user ids => number of approved reports
        user_approved_report_counts = dict()

        for i in self.event_approved_reports:
            current = user_approved_report_counts.get(i.author_id, 0)
            user_approved_report_counts[i.author_id] = current + 1

        for winner_id, reports in sorted(user_approved_report_counts.items(), key=lambda x: x[1], reverse=True):
            count = count + 1
            line = "{count}: <@{id}> ({reports} reports)\n".format(count=str(count), name=str(event.guild.members[winner_id]), reports=str(reports), id=str(winner_id))
            message = message + line
            # stop at 10
            if count == 10:
                break

        message = message + "\nThanks for participating in the Trello Cleaning Event! If you won a prize that needs to be shipped, send a message to Dabbit Prime with a mailing address."
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
            self.save_event_stats(self.config.event_stats_filename)
            shutil.copyfile(self.config.event_stats_filename, "eventstats-archive.json")
            # clear
            self.event_reported_cards = []
            self.delete_reports()

            event.msg.delete()
            event.channel.send_message(":ok_hand: all statistics cleared. archive saved.").after(5).delete()
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
            # clear report stats from user
            self.delete_reports(author_id=user)
            # inform user and bot log
            event.channel.send_message(":ok_hand: cleared reports from user.").after(4).delete()
            self.botlog(event, ":wastebasket: {mod} cleared stats for user {user} with reason {reason}".format(mod=str(event.msg.author), user=str(user), reason=reason))
    
    @Plugin.command('deletereport', "<message_id:snowflake> <reason:str...>", group="event")
    def delete_report(self, event, message_id, reason):
        """Delete a report (author/person to blame when it doesn't work: brxxn)"""
        # check guild
        if event.guild == None:
            return
        
        # check perms
        if self.checkPerms(event, "mod"):
            event.msg.delete()
            # delete report
            self.delete_reports(message_id=message_id)
            # inform user and bot log
            event.channel.send_message(":ok_hand: report deleted.").after(4).delete()
            self.botlog(event, ":wastebasket: {mod} deleted report {message_id} with reason {reason}".format(mod=str(event.msg.author), message_id=str(message_id), reason=reason))
    
    @Plugin.listen("MessageReactionAdd")
    def on_reaction(self, event):
        if event.guild == None:
            return
        if event.emoji.name != "greenTick" and event.emoji.name != "redTick":
            return
        valid_ids = [self.config.event_channel_IDs["ios"], self.config.event_channel_IDs["desktop"], self.config.event_channel_IDs["android"], self.config.event_channel_IDs["linux"]]
        if event.channel.id not in valid_ids:
            return
        member = event.guild.members[event.user_id]
        roles = getattr(self.config, 'mod_roles').values()
        if not any(role in roles for role in member.roles):
            return
        reports = self.search_reports(message_id=event.message_id)
        if len(reports) == 0:
            return
        report = reports[0]
        self.event_pending_reports.remove(report)
        if event.emoji.name == "greenTick":
            report["approved"] = True
            self.event_approved_reports.append(report)
        if event.emoji.name == "redTick":
            self.event_denied_reports.append(report)
        self.botlog(event, ":newspaper: {user} {action} report {message}".format(user=str(member), action="approved" if event.emoji.name == "greenTick" else "denied", message=str(event.message_id)))
        

    def search_reports(self, **kwargs):
        lists_to_search = [self.event_pending_reports, self.event_approved_reports, self.event_denied_reports]
        reports = []
        for search_list in lists_to_search:
            for report in search_list:
                valid = True # all reports are valid unless they fail to meet criteria defined by kwargs, which can be none.
                for k, v in kwargs.items():
                    if report[k] != v:
                        valid = False
                if valid:
                    reports.append(report)
        return reports
    
    def delete_reports(self, **kwargs):
        lists_to_search = [self.event_pending_reports, self.event_approved_reports, self.event_denied_reports]
        for search_list in lists_to_search:
            for report in search_list:
                valid = True # all reports are valid unless they fail to meet criteria defined by kwargs, which can be none.
                for k, v in kwargs.items():
                    if report[k] != v:
                        valid = False
                if valid:
                    search_list.remove(report)
    
    def get_total_reports(self):
        return len(self.event_pending_reports) + len(self.event_denied_reports) + len(self.event_approved_reports)
    
    def get_approved_reports(self):
        return len(self.event_approved_reports)

    def save_event_stats(self, filename):
        try:
            f = open(filename, "w")
            save_dict = {
                "event_reported_cards": self.event_reported_cards,
                "event_pending_reports": self.event_pending_reports,
                "event_approved_reports": self.event_approved_reports,
                "event_denied_reports": self.event_denied_reports
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
            self.event_approved_reports = event_stats_parsed.get("event_approved_reports", [])
            self.event_denied_reports = event_stats_parsed.get("event_denied_reports", [])
            self.event_pending_reports = event_stats_parsed.get("event_pending_reports", [])
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