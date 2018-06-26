import json
import os.path
import time
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

    @Plugin.command("info", '<link:str>')
    def trello_info(self, event, link):
        info = TrelloUtils.getCardInfo(event, link)
        print(info)
        if info is None:
            event.msg.reply("Unable to fetch info about that card, please make sure you have a valid link")
        if info is None or info is False:
            return
        ok = "<:gearYes:459697272326848520>"
        rejected = "<:gearNo:459697272314265600>"
        board = self.config.boards[info["idBoard"]]
        listname = TrelloUtils.getListInfo(info["idList"])["name"]
        archived = info["closed"]

        boardok = info["idBoard"] in self.config.boards.keys()
        listok = info["idList"] in board["lists"]

        message="""
**Board**: {} ({}) {}
**List**: {} ({}) {}
**Archived**: {} {}
""".format(board["name"], info["idBoard"], ok if boardok else rejected, listname, info["idList"], ok if listok else rejected, archived, rejected if archived else ok)
        event.msg.reply(message)

    @Plugin.command("submit", "[submission:str...]")
    def template(self, event, submission:str=None):
        if self.status != "Started":
            return #no event going on, pretend nothing happened #noleeks
        if event.guild is None or event.channel.id != self.config.event_channel: #ignore users running this in the wrong channel, also prevents non hunters from submitting
            return
        if not any(role == self.config.participants_role for role in event.member.roles):
            return

        if submission is None:
            event.msg.reply("{} It seems you're missing parts, the syntax for this command is `+submit <trello link> | <where this ticket should be moved to> | <why it should be moved there and/or new steps>`".format(event.author.mention))
            return

        parts = submission.split("|")
        if len(parts) < 3:
            event.msg.reply("{} It seems you're missing parts, the syntax for this command is `+submit <trello link> | <where this ticket should be moved to> | <why it should be moved there and/or new steps>`".format(event.author.mention))
            return
        if len(parts) > 3:
            parts[2] = "|".join(parts[2:])
        link = parts[0]
        destination = parts[1]
        info = parts[2]

        trello_info = TrelloUtils.getCardInfo(event, link)
        error = None
        if trello_info is False:
            return
        if trello_info is None:
            error = "{} Unable to fetch info about that card, are you sure it exists? Cause i don't feel like playing hide and seek".format(event.author.mention)
        elif trello_info["idBoard"] not in self.config.boards.keys():
            error = "This card is not from one of the discord bug boards, what do you expect me to do with this?"
        elif trello_info['id'] in self.reported_cards.keys():
            report = self.reported_cards[trello_info['id']]
            #hit by sniper?
            timediv = datetime.utcnow() - datetime.utcfromtimestamp(report["report_time"])
            hours, remainder = divmod(int(timediv.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            error = "{} Looks like {} beat you to the punch. Better luck next time {}".format("SNIPED!" if minutes < 2 else "<:dupebutton:341981924010491904>", self.participants[str(report["author_id"])], event.author.mention)
        if error is None:
            board = self.config.boards[trello_info["idBoard"]]
            listname = TrelloUtils.getListInfo(trello_info["idList"])["name"]
            if trello_info["idList"] not in board["lists"]:
                error = "{} This card is in the {} list instead of an event list, thanks for the submission but no thanks".format(event.author.mention, listname)
            elif trello_info["closed"] is True:
                error = "{} _cough cough_ that card has been archived and collected way to much dust for me to do anything with it".format(event.author.mention)

        if error is not None:
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
            message = sanitize.S(message, escape_codeblocks=True)
            if len(message) > 2000:
                event.msg.reply("{} Sorry, but that report is too long for me to process, would mind removing {} characters? Then everything should be fine again.".format(event.author.mention, len(message) - 2000))
                return 
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
            self.participants[str(event.author.id)] = str(event.author)
            event.msg.reply("{} Achievement get! Successfully submitted your first event entry :tada:".format(event.author.mention))
        else:
            #updating name in case it changed
            self.participants[str(event.author.id)] = str(event.author)
            event.msg.reply("{} Thanks for your submission!".format(event.author.mention))

        self.botlog(event, ":inbox_tray: {} has submitted <https://trello.com/c/{}>".format(str(event.author), trello_info['id']))
        self.save_event_stats()



    @Plugin.command('start', group="event")
    def start_command(self, event):
        """Start the event"""
        if self.status != "Scheduled":
            event.msg.reply("Event has already started")
            return

        if event.guild is None:
            return

        # check permissions
        if self.checkPerms(event, "admin"):
            # give bug hunters access to submission channel
            participants_role = event.guild.roles[int(self.config.participants_role)]
            event_channel = event.guild.channels[int(self.config.event_channel)]

            #determine current overrides and if one exists just flip the read channel bit around
            perms = event_channel.overwrites
            view_channel = 1024

            if participants_role.id in perms.keys():

                allow = perms[participants_role.id].allow.add(view_channel)
                deny = perms[participants_role.id].deny.sub(view_channel)
                event_channel.create_overwrite(participants_role, allow = allow, deny=deny)
            else:
                event_channel.create_overwrite(participants_role, allow=view_channel, deny=0)

            self.status = "Started"
            event.channel.send_message("<:gearYes:459697272326848520> Submissions channel unlocked and commands unlocked, here we go")
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
            event.channel.send_message(":ok_hand: Event ended, preparing reports...")
            self.botlog(event, ":lock: {user} ended event (locked all event channels)".format(user=str(event.msg.author)))
            self.status = "Ended"
            self.save_event_stats()

            for reporter, report in self.reported_cards.items():
                message = event_channel.get_message(report["message_id"])
                self.bot.client.api.channels_messages_reactions_create(event_channel.id, message.id, self.config.emojis["yes"])
                self.bot.client.api.channels_messages_reactions_create(event_channel.id, message.id, self.config.emojis["no"])
            event.msg.reply("{} all {} reports have been prepped for approval/denial".format(event.author.mention, len(self.reported_cards)))

    @Plugin.command('cleanuser', "<user:snowflake> <reason:str...>", group="event")
    def clear_user(self, event, user, reason):
        if event.guild is None:
            return
        if self.checkPerms(event, "mod"):
            if not str(user) in self.participants:
                event.msg.reply("This user has not participated in the event")
                return
            else:
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
                event.channel.send_message(":ok_hand: cleared reports from {}.".format(self.participants[str(user)]))
                self.botlog(event, ":wastebasket: {mod} cleared all submissions for {user} with reason {reason}".format(
                    mod=str(event.msg.author), user=self.participants[str(user)], reason=reason))
                del self.participants[str(user)]
                self.save_event_stats()


    @Plugin.command("stats", group="event")
    def event_stats(self, event):
        if not self.checkPerms(event, "admin"):
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

    @Plugin.command("points")
    def points(self, event):

        message = "Your points so far: {}\nThanks for participating in the Trello Event!"

        event.msg.delete()
        points = 0
        for rid, report in self.reported_cards.items():
            if str(event.author.id) == report["author_id"]:
                points += self.config.boards[report["board"]]["points"]
        try:
            event.author.open_dm().send_message(message.format(points))
        except APIException:
            event.channel.send_message("Please enable Direct Messages so I can send you your points.").after(10).delete()

    @Plugin.command("revoke", "<report:str>")
    def revoke(self, event, report):
        if event.msg.channel.id != self.config.event_channel:
            return

        trello_info = TrelloUtils.getCardInfo(event, report)
        if trello_info is None:
            event.msg.reply("I can't even fetch info for that, you sure you reported that one?")
            return
        if not trello_info["id"] in self.reported_cards.keys():
            event.msg.reply("I don't have a report for that card, how do you expect me to edit a non existing thing?")
            return
        report_info = self.reported_cards[trello_info["id"]]
        if report_info["author_id"] != str(event.author.id):
            event.msg.reply("I think there's been a case of mistaken identity here, this report was made by {} and it looks like you are {}".format(self.participants[str(report_info["author_id"])], str(event.author)))
            return

        event.msg.channel.get_message(report_info["message_id"]).delete()
        del self.reported_cards[trello_info["id"]]
        event.msg.reply(":warning: Your submission has been nuked {}!".format(event.author.mention))
        self.botlog(event, ":outbox_tray:  {} has revoked <https://trello.com/c/{}>".format(str(event.author), trello_info['id']))
        self.save_event_stats()

    @Plugin.command("edit", "<details:str...>")
    def edit(self, event, details):
        if event.msg.channel.id != self.config.event_channel:
            return
        print(details)
        parts = details.split("|")
        if len(parts) < 3:
            event.msg.reply("{} It seems you're missing parts, the syntax for this command is `+edit <trello link> | <section (destination or info)> | <new info>`".format(event.author.mention))
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
            new_message = "\n".join(lines[:count-1])
            new_message += "\n**Detailed info**: {}\n{}".format(sanitize.S(info, escape_codeblocks=True),
                                                              "\n".join(lines[-1:]))
        else:
            event.msg.reply("Unknown section")
            return
        if len(new_message) > 2000:
            event.msg.reply(
                "{} Sorry, but would make the report too long for me to process, would mind removing {} characters? Then everything should be fine again.".format(
                    event.author.mention, len(new_message) - 2000))
            return
        print(new_message)
        dmessage.edit(new_message)

        event.channel.send_message("{}, your report has been updated!".format(event.author.mention))
        self.botlog(event, ":pencil: {} has updated the {} of his submission for <https://trello.com/c/{}>".format(str(event.author), section.lower(), trello_info["id"]))

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
        event.msg.reply(":warning: Submission has been nuked {}!".format(event.author.mention))
        self.botlog(event, ":wastebasket: {} has removed <https://trello.com/c/{}>".format(str(event.author), trello_info['id']))


    @Plugin.command("next")
    def next(self, event):
        if not self.checkPerms(event, "admin"):
            return
        event.msg.delete()

        message = "Yes i do have more reports for you!\n\n"
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
                f.write(json.dumps(save_dict, indent=4, skipkeys=True, sort_keys=True, ensure_ascii=False))
            except IOError as ex:
                print("failed to open file: {file}\nstrerror: {strerror}".format(file='eventstats.json', strerror=ex.strerror))
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
                print("failed to open file: {file}\nstrerror: {strerror}".format(file='eventstats.json', strerror=ex.strerror))

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
        if event.channel.id != self.config.event_channel:
            return
        if event.author.id != self.bot.client.api.users_me_get().id:
            if not (event.message.content.startswith("+submit") or event.message.content.startswith("+revoke") or  event.message.content.startswith("+edit") or  event.message.content.startswith("+event")):
                event.message.delete()
                event.message.reply("{} This channel is only event related commands (submit/revoke/edit) command, please go to <#420995378582913030> to discuss submissions".format(event.author.mention))
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