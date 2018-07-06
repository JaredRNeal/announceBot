import json
import os.path
import time
import traceback
from datetime import datetime

from disco.api.http import APIException
from disco.bot import Plugin
from disco.util import sanitize

from commands.config import EventsPluginConfig
from util import TrelloUtils


@Plugin.with_config(EventsPluginConfig)
class Events(Plugin):

    def __init__(self, bot, config):
        super().__init__(bot, config)
        #initialize
        self.queued = False
        self.saving = False
        self.status = "Scheduled"
        self.participants = dict()
        self.reported_cards = dict()

    def load(self, ctx):
        super(Events, self).load(ctx)
        self.load_event_stats()

    def unload(self, ctx):
        self.save_event_stats()
        super(Events, self).unload(ctx)

    @Plugin.command("submit", "[submission:str...]")
    def template(self, event, submission:str=None):
        """Make a new submission"""
        if self.status != "Started":
            return #no event going on, pretend nothing happened #noleeks
        if event.guild is None or event.channel.id != self.config.event_channel: #ignore users running this in the wrong channel, also prevents non hunters from submitting
            return

        help_message = "<@{}> It seems you're missing parts, the syntax for this command is `+submit <trello link> | <where this ticket should be moved to> | <why it should be moved there and/or new steps>`".format(event.author.id)
        if submission is None:
            #no params given, print help info
            event.msg.reply(help_message)
            return

        parts = submission.split("|")
        if len(parts) < 3:
            #missing things we need
            event.msg.reply(help_message)
            return
        if len(parts) > 3:
            #for some reason they used a | in their report, re-assemble it so we don't void things
            parts[2] = "|".join(parts[2:])

        link = parts[0]
        destination = parts[1]
        info = parts[2]

        #fetch the trello info and validate
        trello_info = TrelloUtils.getCardInfo(event, link)
        error = None
        if trello_info is False:
            #wrong type of link, user already informed, we're done here
            return
        if trello_info is None:
            #no info, non existant card or from a private board
            error = "<@{}> Unable to fetch info about that card, are you sure it exists? Cause I don't feel like playing hide and seek.".format(event.author.id)
        elif trello_info["idBoard"] not in self.config.boards.keys():
            #not a discord board
            error = "This card is not from one of the discord bug boards, what do you expect me to do with this?"
        elif trello_info['id'] in self.reported_cards.keys():
            #already reported
            report = self.reported_cards[trello_info['id']]
            #hit by sniper?
            timediv = datetime.utcnow() - datetime.utcfromtimestamp(report["report_time"])
            hours, remainder = divmod(int(timediv.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            error = "<@{}> Looks like {} beat you to the punch. Better luck next time {}".format(event.author.id, self.participants[str(report["author_id"])], "SNIPED!" if minutes < 2 else "<:dupebutton:341981924010491904>")
        if error is None:
            #all good so far
            board = self.config.boards[trello_info["idBoard"]]
            listname = TrelloUtils.getListInfo(trello_info["idList"])["name"]
            if trello_info["idList"] not in board["lists"]:
                #this list is not valid for this event
                error = "<@{}> This card is in the {} list instead of an event list, thanks for the submission but no thanks.".format(event.author.id, listname)
            elif trello_info["closed"] is True:
                #archived card
                error = "<@{}> _cough cough_ that card has been archived and collected way to much dust for me to do anything with it".format(event.author.id)

        if error is not None:
            #card failed one of the checks, inform user and terminate processing
            event.msg.reply(error)
            return
        else:
            # valid submission, processing...

            message = """
**Board**: {} {}
**Source list**:  {}
**Destination**: {}
**Submitted by**: {}
**Detailed info**: {}
**Trello link**: {}""".format(board["name"], board["emoji"], listname, destination, str(event.author), info,
                                          trello_info["shortUrl"])
            #sanitze the entire thing, no pinging or breaking codeblocks
            message = sanitize.S(message, escape_codeblocks=True)
            if len(message) > 2000:
                #discord only accepts essays up to 2000 characters
                event.msg.reply("<@{}> Sorry, but that report is too long for me to process, would mind removing {} characters? Then everything should be fine again.".format(event.author.id, len(message) - 2000))
                return
            #send the submission and clean input
            dmessage = event.msg.reply(message)
            event.msg.delete()

            # add to tracking
            self.reported_cards[trello_info['id']] = dict(
                author_id= str(event.author.id),
                board= trello_info["idBoard"],
                list= trello_info["idList"],
                message_id= dmessage.id,
                status= "Submitted",
                report_time = datetime.utcnow().timestamp()
        )

        if not str(event.author.id) in self.participants.keys():
            #this person has not submitted anything yet, special message
            self.participants[str(event.author.id)] = str(event.author)
            event.msg.reply("<@{}> Achievement get! Successfully submitted your first event entry :tada:".format(event.author.id))
        else:
            event.msg.reply("<@{}> Thanks for your submission!".format(event.author.id))

        self.botlog(event, ":inbox_tray: {} has submitted <https://trello.com/c/{}>".format(str(event.author), trello_info['shortLink']))
        self.save_event_stats()



    @Plugin.command('start', group="event")
    def start_command(self, event):
        """Start the event"""
        if self.checkPerms(event, "admin"):
            # check permissions
            if self.status != "Scheduled":
                event.msg.reply("Event has already started")
                return

            if event.guild is None:
                return
            # give bug hunters access to submission channel
            participants_role = event.guild.roles[int(self.config.participants_role)]
            event_channel = event.guild.channels[int(self.config.event_channel)]

            #determine current overrides and if one exists just flip the read channel bit around
            perms = event_channel.overwrites
            view_channel = 1024

            if participants_role.id in perms.keys():
                #update existing override
                allow = perms[participants_role.id].allow.add(view_channel)
                deny = perms[participants_role.id].deny.sub(view_channel)
                event_channel.create_overwrite(participants_role, allow = allow, deny=deny)
            else:
                #no override present, make a new one
                event_channel.create_overwrite(participants_role, allow=view_channel, deny=0)

            self.status = "Started"
            event.channel.send_message("<:approve:302137375092375553> Submissions channel unlocked and commands unlocked, here we go")
            self.botlog(event, ":unlock: {name} (`{id}`) started the event.".format(name=str(event.msg.author),
                                                                                     id=event.msg.author.id))
            self.save_event_stats()

    @Plugin.command('winners', group="event")
    def event_winners(self, event):
        if not self.checkPerms(event, "admin"):
            return
        # build list of user ids => number of points
        point_count = dict()

        for rid, report in self.reported_cards.items():
            user = str(report["author_id"])
            if not user in point_count.keys():
                point_count[user] = 0
            if report["status"] == "Approved":
                point_count[user] += self.config.boards[report["board"]]["points"]
        to_sort = []
        for uid, number in point_count.items():
            to_sort.append([number, uid])

        count = 0
        message= ""
        for points, uid in sorted(to_sort, key=lambda x: x[0], reverse=True)[:10]:
            count = count + 1
            message += "{}: <@{}> ({} points)\n".format(count, uid, points)
        event.msg.reply(message)

    @Plugin.command('end', group="event")
    def end_event(self, event):
        """End the event, hide channel and prep for approval/denial"""
        if self.checkPerms(event, "admin"):
            participants_role = event.guild.roles[int(self.config.participants_role)]
            event_channel = event.guild.channels[int(self.config.event_channel)]
            perms = event_channel.overwrites
            view_channel = 1024

            if participants_role.id in perms.keys():
                event_channel.create_overwrite(participants_role, allow=0, deny=1024)
            else:
                event_channel.create_overwrite(participants_role, allow=0, deny=1024)
            event.msg.delete()
            event.channel.send_message("<{}> Event ended, preparing submissions...".format(self.config.emojis["yes"]))
            self.botlog(event, ":lock: {user} ended event, prepping the submissions".format(user=str(event.msg.author)))
            self.status = "Ended"
            self.save_event_stats()

            #loop through all submissions and add reactions to it
            for reporter, report in self.reported_cards.items():
                message = event_channel.get_message(report["message_id"])
                self.bot.client.api.channels_messages_reactions_create(event_channel.id, message.id, self.config.emojis["yes"])
                self.bot.client.api.channels_messages_reactions_create(event_channel.id, message.id, self.config.emojis["no"])
            event.msg.reply("<@{}> all {} submissions have been prepped for approval/denial!".format(event.author.id, len(self.reported_cards)))

    @Plugin.command('cleanuser', "<user:snowflake> <reason:str...>", group="event")
    def clear_user(self, event, user, reason):
        """Someone's been so bad we need to remove all their submissions :("""
        if event.guild is None:
            return
        if self.checkPerms(event, "mod"):
            if not str(user) in self.participants:
                #that definitely was the wrong user
                event.msg.reply("This user has not participated in the event")
                return
            else:
                #seperate list to remove as we can't alter the list we are iterating over
                to_remove = []
                for rid, report in self.reported_cards.items():
                    if str(user) == str(report["author_id"]):
                        try:
                            channel = event.guild.channels[self.config.event_channel]
                            channel.get_message(report["message_id"]).delete()
                        except APIException:
                            pass #mod already removed it?
                        to_remove.append(rid)
                for r in to_remove:
                    del self.reported_cards[r]
                event.channel.send_message("<{}> cleared reports from {}.".format(self.config.emojis["yes"], self.participants[str(user)]))
                self.botlog(event, ":wastebasket: {mod} cleared all submissions for {user} with reason {reason}".format(
                    mod=str(event.msg.author), user=self.participants[str(user)], reason=reason))
                del self.participants[str(user)]
                self.save_event_stats()


    @Plugin.command("stats", group="event")
    def event_stats(self, event):
        """Current event stats"""
        if not self.checkPerms(event, "mod"):
            return
        approved = 0
        denied = 0
        for report_id, report in self.reported_cards.items():
            if report["status"] == "Approved":
                approved += 1
            elif report["status"] == "Denied":
                denied += 1
        message = """
Total reports: {}
Number of participants: {}
Approved reports: {}
Denied reports: {}
""".format(len(self.reported_cards), len(self.participants), approved, denied)
        event.msg.reply(message)

    @Plugin.command("points", "<user:snowflake>")
    def points(self, event, user):
        """Points acquired by someone"""
        if not self.checkPerms(event, "mod"):
            return
        event.msg.delete()
        if not str(user) in self.participants.keys():
            message = "This user has not participated in the event yet."
        else:
            message = "Points so far for {}: {}\n"

            points = 0
            for rid, report in self.reported_cards.items():
                if str(user) == report["author_id"] and report["status"] != "Denied":
                    points += self.config.boards[report["board"]]["points"]
            event.msg.reply(message.format(self.participants[str(user)], points))

    @Plugin.command("revoke", "<report:str>")
    def revoke(self, event, report):
        """Revoke a submission"""
        if event.msg.channel.id != self.config.event_channel:
            return

        trello_info = TrelloUtils.getCardInfo(event, report)
        if trello_info is None:
            #invalid card
            event.msg.reply("I can't even fetch info for that, you sure you reported that one?")
            return
        if not trello_info["id"] in self.reported_cards.keys():
            #not reported yet
            event.msg.reply("I don't have a report for that card, how do you expect me to edit a non existing thing?")
            return
        report_info = self.reported_cards[trello_info["id"]]
        if report_info["author_id"] != str(event.author.id):
            #someone else reported
            event.msg.reply("I think there's been a case of mistaken identity here, this report was made by {} and it looks like you are {}".format(self.participants[str(report_info["author_id"])], str(event.author)))
            return

        #delete message and entry
        event.msg.channel.get_message(report_info["message_id"]).delete()
        del self.reported_cards[trello_info["id"]]
        event.msg.reply(":warning: Your submission has been nuked <@{}>!".format(event.author.id))
        self.botlog(event, ":outbox_tray:  {} has revoked <https://trello.com/c/{}>".format(str(event.author), trello_info['shortLink']))
        self.save_event_stats()

    @Plugin.command("edit", "<details:str...>")
    def edit(self, event, details):
        if event.msg.channel.id != self.config.event_channel:
            return
        parts = details.split("|")
        if len(parts) < 3:
            event.msg.reply("<@{}> It seems you're missing parts, the syntax for this command is `+edit <trello link> | <section (destination or info)> | <new info>`".format(event.author.id))
            return
        if len(parts) > 3:
            parts[2] = "|".join(parts[2:])
        link = parts[0]
        section = parts[1].strip(" ").lower()
        info = parts[2]

        trello_info = TrelloUtils.getCardInfo(event, link)
        if trello_info is None:
            event.msg.reply("I can't even fetch info for that, you sure you reported that one?")
            return
        if not trello_info["id"] in self.reported_cards.keys():
            event.msg.reply("I don't have a report for that card, how do you expect me to edit a non existing thing?")
            return
        report_info = self.reported_cards[trello_info["id"]]
        if report_info["author_id"] != str(event.author.id):
            event.msg.reply(
                "I think there's been a case of mistaken identity here, this report was made by {} and it looks like you are {}".format(
                    self.participants[str(report_info["author_id"])], str(event.author)))
            return
        dmessage = event.guild.channels[self.config.event_channel].get_message(report_info["message_id"])
        content:str = dmessage.content
        new_message = ""
        lines = content.splitlines()
        if section == "destination":
            new_message = "\n".join(lines[:2])
            while not lines[2].startswith("**Submitted by**:"):
                lines.pop(2)
            new_message += "\n**Destination**: {}\n{}".format(sanitize.S(info, escape_codeblocks=True), "\n".join(lines[2:]))
        elif section == "info":
            count = 0
            while not lines[count].startswith("**Detailed info**"):
                count += 1
            new_message = "\n".join(lines[:count])
            new_message += "\n**Detailed info**: {}\n{}".format(sanitize.S(info, escape_codeblocks=True),
                                                              "\n".join(lines[-1:]))
        else:
            event.msg.reply("Unknown section")
            return
        if len(new_message) > 2000:
            event.msg.reply(
                "<@{}> Sorry, but would make the report too long for me to process, would mind removing {} characters? Then everything should be fine again.".format(
                    event.author.id, len(new_message) - 2000))
            return
        print(new_message)
        dmessage.edit(new_message)

        event.channel.send_message("<@{}>, your report has been updated!".format(event.author.id))
        self.botlog(event, ":pencil: {} has updated the {} of their submission for <https://trello.com/c/{}>".format(str(event.author), section.lower(), trello_info["shortLink"]))

    @Plugin.command("remove", "<report:str>", group="event")
    def remove_report(self, event, report):
        if not self.checkPerms(event, "mod"):
            return
        trello_info = TrelloUtils.getCardInfo(event, report)
        if trello_info is None:
            event.msg.reply("I can't even fetch info for that, you sure someone reported that one?")
            return
        if not trello_info["id"] in self.reported_cards.keys():
            event.msg.reply(
                "I don't have a report for that card, how do you expect me to edit a non existing thing?")
            return
        report_info = self.reported_cards[trello_info["id"]]
        event.guild.channels[self.config.event_channel].get_message(report_info["message_id"]).delete()
        del self.reported_cards[trello_info["id"]]
        event.msg.reply(":warning: Submission has been nuked <@{}>!".format(event.author.id))
        self.botlog(event, ":wastebasket: {} has removed <https://trello.com/c/{}>".format(str(event.author), trello_info['shortLink']))


    @Plugin.command("next")
    def next(self, event):
        if not self.checkPerms(event, "admin"):
            return
        event.msg.delete()

        message = "Yes I do have more reports for you!\n\n"
        limit = 10
        count = 0
        for reportid, report in self.reported_cards.items():
            if report["status"] == "Submitted":
                message += "<https://canary.discordapp.com/channels/{}/{}/{}>\n".format(event.guild.id, self.config.event_channel, report["message_id"])
                count += 1
            if count >= limit:
                break
        if count == 0:
            message = ":tada: ALL SUBMISSIONS HAVE BEEN PROCESSED :tada:"
        event.channel.send_message(message)

    @Plugin.listen("MessageReactionAdd")
    def on_reaction(self, event):
        if event.channel_id!= self.config.event_channel or event.user_id == self.bot.client.api.users_me_get().id:
            return
        if ":{}:{}".format(event.emoji.name, event.emoji.id) == self.config.emojis["yes"]:
            self.setReportStatus(event, event.message_id, "Approved")
        elif ":{}:{}".format(event.emoji.name, event.emoji.id) == self.config.emojis["no"]:
            self.setReportStatus(event, event.message_id, "Denied")

    def setReportStatus(self, event, message_id, status):
        report = self.findReport(message_id)
        if report is not None:
            report["status"]  = status
            botlog = self.bot.client.api.channels_get(self.config.bot_log)
            botlog.send_message(":newspaper: {} set the status of {} to {} {}"
                                .format(
                str(self.bot.client.api.guilds_members_get(botlog.guild.id, event.user_id)),
                report["message_id"],
                status, "<:{}:{}>".format(event.emoji.name, event.emoji.id)))
            self.save_event_stats()

    def findReport(self, message_id):
        for id, report in self.reported_cards.items():
            if report["message_id"] == message_id:
                return report
        return None

    def save_event_stats(self):
        #TODO: figure out what's going on but for now this prevents data corruption
        if self.saving:
            if not self.queued:
                self.queued = True
                while self.saving:
                    time.sleep(1)
                self.queued = False
            else:
                return
        self.saving = True
        with open("eventstats.json", "w", encoding='utf8') as f:
            try:
                save_dict = dict(
                    reported_cards= self.reported_cards,
                    status= self.status,
                    participants= self.participants
                )
                f.write(json.dumps(save_dict, indent=4, skipkeys=True, sort_keys=False, ensure_ascii=False))
            except IOError as ex:
                print(":rotating_light: <@110813477156720640> save to disc: {file}\nstrerror: {strerror}".format(file='eventstats.json', strerror=ex.strerror))
                traceback.print_exc()
        self.saving = False

    def load_event_stats(self):
        if not os.path.isfile("eventstats.json"):
            return
        with open('eventstats.json', "r", encoding='utf8') as f:
            try:
                event_stats = f.read()
                event_stats_parsed = json.loads(event_stats)
                self.reported_cards = event_stats_parsed.get("reported_cards",dict())
                self.status = event_stats_parsed.get("status", "Scheduled")
                self.participants = event_stats_parsed.get("participants", dict())
            except IOError as ex:
                print(":rotating_light: <@110813477156720640> load from disc: {file}\nstrerror: {strerror}".format(file='eventstats.json', strerror=ex.strerror))
                traceback.print_exc()

    def checkPerms(self, event, role):
        # get roles from the config
        roles = getattr(self.config, str(role) + '_roles').values()
        if any(role in roles for role in event.member.roles):
            return True
        event.msg.reply(":lock: You do not have permission to use this command!")
        self.botlog(event, ":warning: " + str(
            event.msg.author) + " tried to use a command they do not have permission to use.")
        return False

    @Plugin.listen('MessageCreate')
    def no_chat_allowed(self, event):
        if not self.status == "Started":
            return
        #update username cache
        if str(event.author.id) in self.participants.keys():
            if str(event.author) != self.participants[str(event.author.id)]:
                self.participants[str(event.author.id)] = str(event.author)
                #todo, update report or switch them to use id pings
        if event.channel.id != self.config.event_channel:
            return
        if event.author.id != self.bot.client.api.users_me_get().id:
            if not (event.message.content.startswith("+submit") or event.message.content.startswith("+revoke") or  event.message.content.startswith("+edit") or  event.message.content.startswith("+event")):
                event.message.delete()
                event.message.reply("<@{}> This channel is only event related commands (submit/revoke/edit) command, please go to <#420995378582913030> to discuss submissions".format(event.author.id))
            else:
                # make sure incomplete commands get cleaned
                try:
                    event.message.after(11).delete()
                except APIException:
                    pass  # already gone, no need to clean
        elif not event.message.content.startswith("**Board**"):
                try:
                    event.message.after(11).delete()
                except APIException:
                    pass  # already gone, no need to clean


    def botlog(self, event, message):
        channel = event.guild.channels[self.config.bot_log]
        channel.send_message(message)
