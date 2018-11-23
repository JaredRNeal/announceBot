from disco.bot import Config


class AnnounceBotConfig(Config):

    admin_roles = {
        'employee': 411674069528870912,
        'admin': 416261117845700608
        }

    role_IDs = {
        'android': 411674120196194304,
        'linux': 413477593107660800,
        'ios': 413478048890093579,
        'test': 441011171391176704
        }


    mod_roles = {
        'emplyee': 411674069528870912,
        'admin': 416261117845700608
    }

    channel_IDs = {
        'mod_Channel': 411674296054710273,
        'android': 413446997253554186,
        'iOS': 413447018816733195,
        'desktop': 413447049040756739,
        'test': 411674296054710273,
        'bot_log': 455847829676752916
        }

    #relevant channel IDs in the Test Server:
    event_channel_IDs = {
    'ios': 425682219596644353,
    'android': 425682234540818442,
    'desktop': 425682251817287700,
    'linux': 425682269609525255,
    'prizes': 425682284809814028,
    'rules': 425682305357578250,
    'claimed_fixed': 425682330494042117
    }

    channels_to_lockdown = {
        #test server channel IDs
        'bug': 448943946534486017,
        'android': 425682234540818442,
        'desktop': 425682251817287700,
        'ios': 425682219596644353,
        'linux': 425682269609525255

    }

    role_IDs_to_lockdown = {
        'not_employee': 411674095881814017,
        'everyone': 411673927698350100
    }
    """

    channel_IDs = {
        'android': 411645018105970699,
        'bug': '421790860057903104',
        'canary': 411645098946985984,
        'desktop': 411645098946985984,
        'ios': 411645199866003471,
        'linux': 411645098946985984,
        'mac': 411645098946985984,
        'mod_Channel': 281283303326089216,
        'windows': 411645098946985984,
        'test': 281283303326089216,
        'bot_log': 455874979146235916
    }

    # relevant channel IDs in DTesters:
    event_channel_IDs = {
        'ios': 424032686622113794,
        'android': 424032786664390656,
        'desktop': 424032874900094989,
        'linux': 424032956856926219,
        'prizes': 406167192543952897,
        'rules': 406151195632336907,
        'claimed_fixed': 406165473856585739
    }
    """

    event_stats_filename = "eventstats.json"  # event stats are saved to this location.

    emojis = {
        "red_tick": "312314733816709120",
        "green_tick": "312314752711786497"
    }


class EventsPluginConfig(Config):
    emojis = {
        "yes": ":gearYes:459697272326848520",
        "no": ":gearNo:459697272314265600"
    }

    boards = {}
    event_channel = 0


class StatsPluginConfig(Config):
    queue_channel = 253923313460445184
    queue_summary = {
        "title": "Bug Approval Queue Summary",
        "message": [
      "There are **{{total_reports:all}}** reports in the queue right now. \n",
      "__**Android**__ - <:android:332598085782077451> \n Android has **{{total_reports:232568032394870784}}** open reports. \n There are **{{stale_reports:232568032394870784,24}}** reports that have had no action within the last 24 hours. \n This is the [Oldest Report]({{oldest_report:232568032394870784}}). \n",
      "__**iOS**__ - :iphone: \n iOS has **{{total_reports:202491590390841344}}** open reports. \n There are **{{stale_reports:202491590390841344,24}}** reports that have had no action within the last 24 hours. \n This is the [Oldest Report]({{oldest_report:202491590390841344}}). \n",
      "__**Desktop**__ - :desktop: \n Desktop has **{{total_reports:197038744908333066}}** open reports. \n There are **{{stale_reports:197038744908333066,24}}** reports that have had no action within the last 24 hours. \n This is the [Oldest Report]({{oldest_report:197038744908333066}}). \n",
      "__**Linux**__ - :penguin: \n Linux has **{{total_reports:238073742624948225}}** open reports. \n There are **{{stale_reports:238073742624948225,24}}** reports that have had no action within the last 24 hours. \n This is the [Oldest Report]({{oldest_report:238073742624948225}}). \n",
      "This is the [Oldest Report]({{oldest_report:all}}) in the queue."
    ],        "channel": 506509300127236097,
        "color": '#7289DA'
    }


class ExperiencePluginConfig(Config):
    channels = {
        "bot_log": 0,
        "prize_log": 0,
        "bug_hunter_general_chat": 217764019661045761
    }

    rewards = {
        "approve_deny": 5,
        "canrepro_cantrepro": 3,
        "attach": 5,
        "submit": 25,
    }

    reward_limits = {
        "approve_deny": 5,
        "canrepro_cantrepro": 3,
        "attach": 2,
        "submit": 200
    }

    cooldown_map = {
        "approve_deny": "Approve/Deny",
        "canrepro_cantrepro": "Can/Can't Repro",
        "submit": "Submit"
    }

    store = [
        {
            "title": "Bug Squasher role (for a week)",
            "cost": 250,
            "description": "Get the super cool Bug Squasher role because you squash bugs!"
        },
        {
            "title": u"Fehlerjager role",
            "cost": 500,
            "description": u"Show off that you're a legendary Bug Hunter with the Fehlerjager role!"
        },
        {
            "title": "Bug Hunter Badge",
            "cost": 750,
            "description": "Want to show off to your friends your bug-hunting skills? Get an *exclusive* badge on your "
                           "Discord profile!"
        }
    ]


class GuideConfig(Config):
    guides = {
        "guide": {
            "title": "DTesters Guide",
            "description": "A quick reference guide for all things Discord Testers.",
            "pages": [
                {
                    "title": "Table of Contents",
                    "description": "",
                    "fields": [{
                        "name": "test field",
                        "value": "test value"
                    }],
                    "table_of_contents": True
                },
                {
                    "title": "Test Page 1",
                    "description": "TEST",
                    "fields": [{
                        "name": "test",
                        "value": "Testing stuff. *test* test test **test**!"
                    }]
                },
                {
                    "title": "Test Page 2",
                    "description": "TEST",
                    "fields": [{
                        "name": "test",
                        "value": "Testing more stuff. *test test* test test **test**! (2)"
                    }]
                }
            ]
        }
    }
    welcome_message = "Welcome to Discord Testers! Read this guide for information on Discord Testers. Click on the reactions to change pages for more information!"


class NotifyPluginConfig(Config):
    channels = {
        'bot-log': 455874979146235916,
        'denied-bugs': 327914056591736834,
        'bug-approval-queue': 253923313460445184
    }


class ChatInteractionsConfig(Config):
    # Love should be easier to come across.
    hug_cost = 2
    fight_cost = 2
    bunny_cost = 5

    hug_msgs = [
        'just gave you a big big hug!'
    ]

    fight_msgs = [
        ", but instead slipped on some jam and fell right into Dabbit, who is not pleased.",
        " with a transformer.",
        ", but creates a black hole and gets sucked in.",
        " with poutine.",
        ", but they slipped on a banana peel",
        " and in the end, the only victor was the coffin maker.",
        ", and what a fight it is!  Whoa mama!",
        ", with two thousand blades!",
        ", but he fell into a conveniently placed manhole!",
        ", but they tripped over a rock and fell in the ocean",
        ", but they hurt themselves in confusion",
        ". HADOUKEN!",
        " with a pillow",
        " with a large fish",
        ", but they stumbled over their shoelaces",
        ", but they missed",
        " with a burnt piece of toast",
        ", but it wasn't very effective"
    ]

class GitHubConfig(Config):
    source_code_location = "https://github.com/JaredRNeal/announceBot"
