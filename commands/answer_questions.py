
from disco.api.http import APIException
from disco.bot import Plugin

from commands.config import AnnounceBotConfig

from util.GlobalHandlers import command_wrapper, log_to_bot_log, handle_exception

import time


class answer_questions(Plugin):

    bot_IDs = {
      'testbot': 422786385015996439,
      'rowboat': 232921983317180416,
      'outboard': 501816123507998730,
      'evilDabbit': 413393370770046976,
      'bugbot': 240545475118235648
      }

    advanced_roles = {
      'employee': 197042389569765376,
      'admin': 197042322939052032,
      'modinator': 440322144593772545,
      'bug_hunter': 197042209038663680,
      'test_role': 411674069528870912
      }

    @Plugin.listen("MessageCreate")
    def answer_frequent_questions(self, event):
        if event.author.id in self.bot_IDs.values():
            return
        for role in event.member.roles:
            if role in self.advanced_roles.values():
                return
        self.FAQ_dictionary = self.get_questions_as_a_dict()
        for key in self.FAQ_dictionary.keys():
            if key in event.content:
                time.sleep(3)
                event.reply(self.FAQ_dictionary[key].replace("\\n", "\n"))
                log_to_bot_log(self.bot, f":clock1: {event.author} activated the auto response.")

    @Plugin.command("addfaq", parser=True)
    @Plugin.add_argument("-f", "--FAQ_Key", help='The phrase you want to trigger the response.')
    @Plugin.add_argument("-c", "--FAQ_Content", help="The content of the message you want the bot to respond with.")
    @command_wrapper(perm_lvl=2)
    def add_new_faq(self, event, args):
        f = open("faqs.txt", "a")
        # Checks to see if the FAQ_Key is unique.
        aDict = self.get_questions_as_a_dict()
        for key in aDict:
            if key == args.FAQ_Key:
                event.msg.reply("Sorry! That FAQ name is already in use.")
                return
        # if the faq name is acceptable, add it to the text file
        args.FAQ_Content = args.FAQ_Content.replace("\n", "\\n")
        f.write(f"\n{args.FAQ_Key}:{args.FAQ_Content}")
        f.close()
        event.msg.reply("New FAQ has been added!")

    def get_questions_as_a_dict(self):
        faq_dict = {}
        with open("faqs.txt") as raw_data:
            for item in raw_data:
                if ':' in item:
                    key,value = item.split(':', 1)
                    faq_dict[key] = value
        return faq_dict

    @Plugin.command("faqlist")
    @command_wrapper(perm_lvl=2)
    def show_all_available_questions(self, event):
        message = ""
        aDict = self.get_questions_as_a_dict()
        for key in aDict:
            message += f"{key}\n"
        event.msg.reply(f"The following are all of the available faqs:\n ```\n{message}```")

    @Plugin.command("removefaq", "<FAQ_Key:str>")
    @command_wrapper(perm_lvl=2)
    def remove_faq_from_txt(self, event, FAQ_Key):
        aDict = self.get_questions_as_a_dict()
        if FAQ_Key in aDict.keys():
            aDict.pop(FAQ_Key)
        else:
            event.msg.reply("Sorry, I can't find an existing FAQ with that name.")
            return
        # now we need to recreate the txt file and write that to the fileself.
        FAQ_File = aDict.items()
        f = open("faqs.txt", "w")
        msg = ""
        for key,value in FAQ_File:
            msg += f"{key}:{value}\n"
        f.write(msg)
        f.close()
        event.msg.reply("FAQ removed successfully!")

    @Plugin.command("faq", "<FAQ_Key:str...>")
    @command_wrapper(perm_lvl=2)
    def force_post_faq_content(self, event, FAQ_Key):
        aDict = self.get_questions_as_a_dict()
        for key in aDict:
            if key == FAQ_Key:
                event.msg.reply(aDict[key].replace("\\n", "\n"))
                return
        event.msg.reply(f"Sorry, I can't find an FAQ with the name `{FAQ_Key}`")



#hello world
