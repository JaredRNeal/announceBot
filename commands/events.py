import time
from datetime import datetime

from disco.bot import Plugin
from disco.api.http import APIException
from commands.config import EventsPluginConfig
import os.path
import json
import shutil
from util import TrelloUtils


@Plugin.with_config(EventsPluginConfig)
class Events(Plugin):

    def load(self, ctx):
        super(Events, self).load(ctx)
        self.reported_cards = dict()
        self.partipants = dict()
        self.status = "Scheduled"
        self.saving = False
        self.queued = False
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
        ok = "<:greentickgear:458907588986273812>"
        rejected = "<:redtickgear:458907619864739841>"
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

    @Plugin.command("submit", "<link:str>, <destination:str>, <info:str...>")
    def template(self, event, link, destination, info):
        if self.status != "Started":
            return #no event going on, pretend nothing happened #noleeks
        if event.guild is None or event.channel.id != self.config.event_channel: #ignore users running this in the wrong channel, also prevents non hunters from submitting
            return
        trello_info = TrelloUtils.getCardInfo(event, link)
        print(trello_info)
        error = None
        if trello_info is None:
            error = "Unable to fetch info about that card, are you sure it exists? Cause i don't feel like playing hide and seek"
        if trello_info["idBoard"] not in self.config.boards.keys():
            error = "This card is not from one of the discord bug boards, what do you expect me to do with this?"
        if trello_info['id'] in self.reported_cards.keys():
            report = self.reported_cards[trello_info['id']]
            #hit by sniper?
            timediv = datetime.utcnow() - datetime.utcfromtimestamp(report["report_time"])
            hours, remainder = divmod(int(timediv.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            print(self.partipants)
            error = "{} Looks like {} beat you to the punch. Better luck next time!".format("SNIPED!" if minutes < 2 else "<:dupebutton:341981924010491904>", self.partipants[str(report["author_id"])])
        if error is None:
            board = self.config.boards[trello_info["idBoard"]]
            listname = TrelloUtils.getListInfo(trello_info["idList"])["name"]
            if trello_info["idList"] not in board["lists"]:
                error = "This card is in the {} list instead of an event list, thanks for the submission but no thanks".format(listname)
            elif trello_info["closed"] is True:
                error = "_cough cough_ that card has been archived and collected way to much dust for me to do anything with it"

        if error is not None:
            event.msg.reply(error).after(15).delete()
            event.msg.delete()
            return
        else:
            # valid submission, processing...
            event.msg.delete()

            message = """
**Board**: {} {}
**Source list**:  {}
**Destination**: {}
**Submitted by**: {}
**Additional info**: {}
**Trello link**: {}""".format(board["name"], board["emoji"], listname, destination, str(event.author), info,
                                          trello_info["shortUrl"])
            dmessage = event.msg.reply(message)

        # add to tracking
            self.reported_cards[trello_info['id']] = dict(
                author_id= str(event.author.id),
                board= trello_info["idBoard"],
                list= trello_info["idList"],
                message_id= dmessage.id,
                status= "Submitted",
                report_time = datetime.utcnow().timestamp()
        )

        to_clean = None
        if not event.author.id in self.partipants.keys():
            self.partipants[str(event.author.id)] = str(event.author)
            to_clean = event.msg.reply("Achievement get! Successfully submitted your first event entry :tada:")
            print(self.partipants)
        else:
            #updating name in case it changed
            self.partipants[str(event.author.id)] = str(event.author)

        self.save_event_stats()
        if to_clean is not None:
            to_clean.after(15).delete()



    @Plugin.command('start', group="event")
    def start_command(self, event):
        """Start the event"""

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
                print(perms[participants_role.id].deny.to_dict())
                print(perms[participants_role.id].deny.sub(view_channel).to_dict())
                allow = perms[participants_role.id].allow.add(view_channel)
                deny = perms[participants_role.id].deny.sub(view_channel)
                event_channel.create_overwrite(participants_role, allow = allow, deny=deny)
            else:
                event_channel.create_overwrite(participants_role, allow=view_channel, deny=0)

            self.status = "Started"
            event.channel.send_message("<:greentickgear:458907588986273812> Submissions channel unlocked and commands unlocked, here we go")
            self.botlog(event, ":unlock: {name} (`{id}`) started the event.".format(name=str(event.msg.author),
                                                                                     id=event.msg.author.id))
            self.save_event_stats()

    @Plugin.command('winners', group="event")
    def event_winners(self, event):
        """Find 1st-10th winners in bug reporting (author/person to blame when it doesn't work: brxxn)"""
        # check guild
        if event.guild is None:
            return

        if not self.checkPerms(event, "admin"):
            return

        message = "Total amount of approved reports: {total_amount}\nWinners are:\n\n".format(
            total_amount=str(self.get_approved_reports()))

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

        message = message + "\nThanks for participating in the Trello Cleaning Event! If you won a prize that needs " \
                            "to be shipped, send a message to Dabbit Prime with a mailing address."
        event.msg.delete()
        event.channel.send_message(message)

    @Plugin.command('end', group="event")
    def end_event(self, event):
        """End the event (author/person to blame when it doesn't work: brxxn)"""
        # check guild
        if event.guild is None:
            return

        if self.checkPerms(event, "admin"):
            bh_role = event.guild.roles[self.config.role_IDs["bug"]]
            lock_channels = ["ios", "android", "desktop", "linux", "claimed_fixed"]
            for i in lock_channels:
                channel = event.guild.channels[self.config.event_channel_IDs[i]]
                # allow: none; deny: view channel, send message, add reactions
                channel.create_overwrite(bh_role, allow=0, deny=2112)
            event.msg.delete()
            event.channel.send_message(":ok_hand: event ended - channels locked. "
                                       "note that statistics have **not** been reset.").after(5).delete()
            self.botlog(event, ":lock: {user} ended event (locked all event channels)".format(
                user=str(event.msg.author)))

    @Plugin.command('clearall', group="event")
    def clear_stats(self, event):
        """Clear all statistics (author/person to blame when it doesn't work: brxxn)"""
        # check guild
        if event.guild is None:
            return

        # check perms
        if self.checkPerms(event, "admin"):
            self.save_event_stats(self.config.event_stats_filename)
            shutil.copyfile(self.config.event_stats_filename, "eventstats-archive.json")
            # clear
            self.reported_cards = []
            self.delete_reports()

            event.msg.delete()
            event.channel.send_message(":ok_hand: all statistics cleared. archive saved.").after(5).delete()
            self.botlog(event, ":wastebasket: {user} cleared all statistics for the event".format(
                user=str(event.msg.author)))

    @Plugin.command('clearuser', "<user:snowflake> <reason:str...>", group="event")
    def clear_user(self, event, user, reason):
        """Clear user statistics (author/person to blame when it doesn't work: brxxn)"""
        # check guild
        if event.guild is None:
            return

        # check perms
        if self.checkPerms(event, "mod"):
            event.msg.delete()
            # clear report stats from user
            self.delete_reports(author_id=user)
            # inform user and bot log
            event.channel.send_message(":ok_hand: cleared reports from user.").after(4).delete()
            self.botlog(event, ":wastebasket: {mod} cleared stats for user {user} with reason {reason}".format(
                mod=str(event.msg.author), user=str(user), reason=reason))

    @Plugin.command('deletereport', "<message_id:snowflake> <reason:str...>", group="event")
    def delete_report(self, event, message_id, reason):
        """Delete a report (author/person to blame when it doesn't work: brxxn)"""
        # check guild
        if event.guild is None:
            return

        # check perms
        if self.checkPerms(event, "mod"):
            event.msg.delete()
            # delete report
            self.delete_reports(message_id=message_id)
            # inform user and bot log
            event.channel.send_message(":ok_hand: report deleted.").after(4).delete()
            self.botlog(event, ":wastebasket: {mod} deleted report {message_id} with reason {reason}".format(
                mod=str(event.msg.author), message_id=str(message_id), reason=reason))

    @Plugin.command("points")
    def points(self, event):
        total_reports = len(self.search_reports(author_id=event.msg.author.id))
        unverified_reports = len(self.search_reports(author_id=event.msg.author.id, approved=False, denied=False))
        verified_reports = len(self.search_reports(author_id=event.msg.author.id, approved=True))

        message = "Unverified Reports: {unverified}\nVerified (Approved) Reports: {verified}\nTotal Reports: {total}" \
                  "\n\nThanks for participating in the Trello Event!"

        event.msg.delete()
        try:
            dm_channel = event.msg.author.open_dms()
            dm_channel.send_message(message.format(
                unverified=str(unverified_reports),
                verified=str(verified_reports),
                total=str(total_reports)
            ))
        except APIException:
            event.channel.send_message("Please enable Direct Messages so I can send you your points.").after(5).delete()

    @Plugin.command("revoke", "<message_id:snowflake>", group="event")
    def revoke(self, event, message_id):
        if event.guild is None:
            return

        event.msg.delete()

        reports = self.search_reports(author_id=str(event.msg.author.id), message_id=str(message_id))
        if len(reports) == 0:
            event.channel.send_message("Couldn't find any reports made by you with message ID `{id}`".format(
                id=str(message_id)
            )).after(10).delete()
            return

        # TODO change from event.channel.id to proper channel
        try:
            message = event.guild.channels[event.channel.id].get_message(reports[0].message_id)
            message.delete()
        except APIException:
            event.channel.send_message("This is not the report you are looking for.")\
                .after(10).delete()
            return

        self.delete_reports(author_id=str(event.msg.author.id), message_id=str(message_id))
        event.channel.send_message(":ok_hand: revoked your submission.")

    @Plugin.command("edit", "<message_id:snowflake> <edit_key:str> <edit_value:str...>")
    def edit(self, event, message_id, edit_key, edit_value):
        if event.guild is None:
            return

        event.msg.delete()
        valid_keys = ["name", "message"]
        if edit_key.lower() not in valid_keys:
            event.channel.send_message("invalid key. valid keys are `name, message`")
            return

        reports = self.search_reports(author_id=str(event.msg.author.id), message_id=str(message_id))
        if len(reports) == 0:
            event.channel.send_message("Couldn't find any reports made by you with message ID `{id}`".format(
                id=str(message_id)
            )).after(10).delete()
            return

        edited_reports = self.edit_reports(edit_key.lower(), edit_value, author_id=str(event.msg.author.id), message_id=str(message_id))

        modified_message = "{name} (`{id}`) reported {a_or_an} {bug_type} bug: `{message}`, {link}".format(
            name=str(event.msg.author),
            id=str(event.msg.author.id),
            a_or_an="an" if edited_reports[0].category == "ios" or edited_reports[0].category == "android" else "a",
            bug_type=edited_reports[0].category,
            message=edited_reports[0].message,
            link=edited_reports[0].link
        )

        # TODO change from event.channel.id to proper channel
        try:
            message = event.guild.channels[event.channel.id].get_message(edited_reports[0].message_id)
            message.edit(modified_message)
        except APIException:
            event.channel.send_message("This is not the report you are looking for.") \
                .after(10).delete()
            return

        event.channel.send_message(":ok_hand: edited report!")


    @Plugin.command("next", "[category:str]", group="event")
    def next(self, event, category):
        if event.guild is None:
            return

        event.msg.delete()

        if not self.checkPerms(event, "admin"):
            return

        message = "Here are some reports that are still pending:\n\n"

        parsed_category = ""
        if category is not None:
            valid_categories = ["desktop", "ios", "android", "linux"]
            if category.lower() not in valid_categories:
                event.msg.send_message("invalid category. valid categories: `desktop, ios, android, linux`").after(10).delete()
                return
            parsed_category = category.lower()

        reports = self.search_reports(approved=False, denied=False, category=parsed_category) if parsed_category != "" \
            else self.search_reports(approved=False, denied=False)

        if len(reports) == 0:
            message = "It seems that there are no more pending bugs in the queue! :)"

        count = 0
        for report in reports:
            count = count + 1
            link = "https://discordapp.com/channels/{guild}/{channel}/{message}".format(
                guild=event.guild,
                channel=event.channel,
                message=event.message)
            message = message + "{count}: {link}\n".format(count=count, link=link)
            if count == 5:
                break

        event.channel.send_message(message)

    @Plugin.listen("MessageReactionAdd")
    def on_reaction(self, event):
        if event.guild is None:
            return
        if event.emoji.name != "greenTick" and event.emoji.name != "redTick":
            return
        valid_ids = [self.config.event_channel_IDs["ios"], self.config.event_channel_IDs["desktop"],
                     self.config.event_channel_IDs["android"], self.config.event_channel_IDs["linux"]]
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
        self.botlog(event, ":newspaper: {user} {action} report {message}".format(
            user=str(member),
            action="approved" if event.emoji.name == "greenTick" else "denied",
            message=str(event.message_id)))

    def search_reports(self, **kwargs):
        lists_to_search = [self.event_pending_reports, self.event_approved_reports, self.event_denied_reports]
        reports = []
        for search_list in lists_to_search:
            for report in search_list:
                valid = True  # all reports are valid unless they fail to meet criteria defined by kwargs, which can be none.
                for k, v in kwargs.items():
                    if report[k] != v:
                        valid = False
                if valid:
                    reports.append(report)
        return reports

    def edit_reports(self, key, value, **kwargs):
        lists_to_search = [self.event_pending_reports, self.event_approved_reports, self.event_denied_reports]
        reports = []
        for search_list in lists_to_search:
            for report in search_list:
                valid = True  # all reports are valid unless they fail to meet criteria defined by kwargs, which can be none.
                for k, v in kwargs.items():
                    if report[k] != v:
                        valid = False
                if valid:
                    report[key] = value
                    reports.append(report)
        return reports

    def delete_reports(self, **kwargs):
        lists_to_search = [self.event_pending_reports, self.event_approved_reports, self.event_denied_reports]
        for search_list in lists_to_search:
            for report in search_list:
                valid = True  # all reports are valid unless they fail to meet criteria defined by kwargs, which can be none.
                for k, v in kwargs.items():
                    if report[k] != v:
                        valid = False
                if valid:
                    search_list.remove(report)

    def get_total_reports(self):
        return len(self.event_pending_reports) + len(self.event_denied_reports) + len(self.event_approved_reports)

    def get_approved_reports(self):
        return len(self.event_approved_reports)

    def save_event_stats(self):
        if self.saving:
            if not self.queued:
                self.queued = True
                print("save in progress, took the queue slot")
                while self.saving:
                    time.sleep(1)
                self.queued = False
                print("save finished, freed up the queue slot")
            else:
                return
        self.saving = True
        print("starting save")
        with open("eventstats.json", "w") as f:
            try:
                save_dict = dict(
                    reported_cards= self.reported_cards,
                    status= self.status,
                    participants= self.partipants
                )
                print(save_dict)
                f.write(json.dumps(save_dict))
            except IOError as ex:
                print("failed to open file: {file}\nstrerror: {strerror}".format(file='eventstats.json', strerror=ex.strerror))
        self.saving = False
        print("Save complete")

    def load_event_stats(self):
        if not os.path.isfile("eventstats.json"):
            return
        with open('eventstats.json', "r") as f:
            try:
                event_stats = f.read()
                event_stats_parsed = json.loads(event_stats)
                self.reported_cards = event_stats_parsed.get("reported_cards",dict())
                self.status = event_stats_parsed.get("Status", "Scheduled")
                self.partipants = event_stats_parsed.get("participants", dict())
            except IOError as ex:
                print("failed to open file: {file}\nstrerror: {strerror}".format(file='eventstats.json', strerror=ex.strerror))

    def checkPerms(self, event, type):
        # get roles from the config
        roles = getattr(self.config, str(type) + '_roles').values()
        if any(role in roles for role in event.member.roles):
            return True
        event.msg.reply(":lock: You do not have permission to use this command!")
        self.botlog(event, ":warning: " + str(
            event.msg.author) + " tried to use a command they do not have permission to use.")
        return False

    def botlog(self, event, message):
        channel = event.guild.channels[self.config.bot_log]
        channel.send_message(message)