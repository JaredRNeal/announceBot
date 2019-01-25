from commands import BasePlugin, BaseConfig
from disco.types.message import MessageEmbed
import re
from util.GlobalHandlers import command_wrapper


class WebhookConfig(BaseConfig):
    fixed_queue = 535591333226741791
    verification_threshold = 3
    reward_limits = {
        "approve_deny": 5,
        "canrepro_cantrepro": 5,
        "attach": 0,
        "submit": 200,
        "verify": 5
    }
    rewards = {
        "approve_deny": 5,
        "canrepro_cantrepro": 3,
        "submit": 25,
        "attach": 0,
        "verify": 3
    }
    fixed_list = [
        '581286a2c1e6cd4831c862ca',
        '58d178ec961e15df2e742cb7',
        '57f3de4a5e37d8142fde0313',
        '5bce3dcf8098df6e897bc707',
        '5846fa01674a0ee22d41ec5d'
    ]
    fixed_dict = {
        '57f2a306ca14741151990900':
            {
                'ver': '57fe7f78ddde6b37323bd670',
                'fix': '57f2a37248089a5e6a0bf9b6'
            },
        '57f2d333b99965a6ba8cd7e0':
            {
                'ver': '57fe7f909aa7fe383d56406b',
                'fix': '5858412042dabceed89d7d83'
            },
        '5771673855f47b547f2decc3':
            {
                'ver': '57716787a06d09cf7e0dd1ca',
                'fix': '577167f59d3739f090f8fab2'
            },
        '5bc7b4adf7d2b839fa6ac108':
            {
                'ver': '5bce483227f80b2351d5f8b8',
                'fix': '5c40ff6aac035f1e8ff690ab'
            },
        '5846f7fdfa2f44d1f47267b0':
            {
                'ver': '5846f9fdcab93bbf78e80e04',
                'fix': '5846fa1918828cc3819e2382'
            }

    }
    board_to_emoji = {
        '57f2a306ca14741151990900': '<:android:373636853053521920>',
        '57f2d333b99965a6ba8cd7e0': ':apple:',
        '5771673855f47b547f2decc3': ':desktop:',
        '5bc7b4adf7d2b839fa6ac108': ':department_store:',
        '5846f7fdfa2f44d1f47267b0': ':penguin:'
    }


@BasePlugin.with_config(WebhookConfig)
class WebhookPlugin(BasePlugin):
    def load(self, ctx):
        super(WebhookPlugin, self).load(ctx)
        self.verifications = self.client.verification.verifications
        self.reports = self.client.reactions.reports

    @BasePlugin.command("revoke", parser=True)
    @BasePlugin.parser.add_argument('card', type=str)
    @command_wrapper(perm_lvl=1)
    def revoke(self, event, args):
        if not (event.channel.id == self.config.fixed_queue and event.msg.author.id != self.state.me.id):
            event.msg.delete()
            return

        if not args.card:
            event.msg.delete()
            return

        if not self.reports.find_one({'_id': args.card}):
            event.msg.delete()
            return

        _report = self.reports.find_one({'_id': args.card})

        self.verifications.find_one_and_delete(
            {
                'user_id': str(event.msg.author.id),
                'shortLink': _report.get('shortLink')
            }
        )

        self.bot.client.api.channels_messages_modify(
            self.config.fixed_queue,
            _report.get('message_id'),
            embed=self.create_card_embed(_report)
        )

        event.msg.delete()

    @BasePlugin.command("approve", parser=True)
    @BasePlugin.parser.add_argument('card', type=str)
    @BasePlugin.parser.add_argument('reason', type=str)
    @command_wrapper(perm_lvl=1)
    def approve(self, event, args):
        if not (event.channel.id == self.config.fixed_queue and event.msg.author.id != self.state.me.id):
            event.msg.delete()
            return

        if not self.reports.find_one({'_id': args.card}):
            event.msg.delete()
            return

        verification = {
            'user_id': '',
            'name': '',
            'shortLink': '',
            'reason': '',
            'stance': ''
        }

        verification['user_id'] = str(event.msg.author.id)
        verification['name'] = str(event.msg.author)

        if args.card:
            verification['shortLink'] = self.reports.find_one({'_id': args.card}).get('shortLink')

        if args.reason:
            verification['reason'] = args.reason

        verification['stance'] = 'approve'

        if self.verifications.find_one({'user_id': verification['user_id'], 'shortLink': verification['shortLink'], 'stance': verification['stance']}):
            event.msg.delete()
            return

        self.verifications.find_one_and_delete({'user_id': verification['user_id'], 'shortLink': verification['shortLink']})
        self.verifications.insert_one(verification)
        _report = self.reports.find_one({'shortLink': verification['shortLink']})
        self.bot.client.api.channels_messages_modify(
            event.msg.channel_id,
            _report.get('message_id'),
            embed=self.create_card_embed(_report)
        )
        _trellostring = "Can't reproduce.\n" + verification.get('reason') +  '\n\n' + verification.get('name')
        self.trello_client.add_comment(verification.get('shortLink'), _trellostring)

        tally = {}
        tally['approve'] = self.tally_approvals(verification)
        tally['deny'] = self.tally_denials(verification)
        if tally['approve'] >= self.config.verification_threshold:
            report_board = self.trello_client.get_card(_report.get('shortLink')).get('idBoard')
            self.trello_client.to_list(_report.get('shortLink'), self.config.fixed_dict.get(report_board).get('fix'))
            rplymsg = event.msg.reply('Moving to Verified Fixed!')
            rplymsg.delete()
            self.bot.client.api.channels_messages_delete(
                event.msg.channel_id,
                _report.get('message_id')
            )

        if tally['deny'] >= self.config.verification_threshold:
            report_board = self.trello_client.get_card(_report.get('shortLink')).get('idBoard')
            self.trello_client.to_list(_report.get('shortLink'), self.config.fixed_dict.get(report_board).get('ver'))
            rplymsg = event.msg.reply("Moving back to Verified Bugs!")
            rplymsg.delete()
            self.bot.client.api.channels_messages_delete(
                event.msg.channel_id,
                _report.get('message_id')
            )

        self.shared_handle_action(verification['user_id'], 'verify', True)

        event.msg.delete()

    @BasePlugin.command("deny", parser=True)
    @BasePlugin.parser.add_argument('card', type=str)
    @BasePlugin.parser.add_argument('reason', type=str)
    @command_wrapper(perm_lvl=1)
    def deny(self, event, args):
        if not (event.channel.id == self.config.fixed_queue and event.msg.author.id != self.state.me.id):
            event.msg.delete()
            return

        if not self.reports.find_one({'_id': args.card}):
            event.msg.delete()
            return

        verification = {
            'user_id': '',
            'name': '',
            'shortLink': '',
            'reason': '',
            'stance': ''
        }

        verification['user_id'] = str(event.msg.author.id)
        verification['name'] = str(event.msg.author)

        if args.card:
            verification['shortLink'] = self.reports.find_one({'_id': args.card}).get('shortLink')

        if args.reason:
            verification['reason'] = args.reason

        verification['stance'] = 'deny'

        if self.verifications.find_one({'user_id': verification['user_id'], 'shortLink': verification['shortLink'], 'stance': verification['stance']}):
            event.msg.delete()
            return

        self.verifications.find_one_and_delete({'user_id': verification['user_id'], 'shortLink': verification['shortLink']})
        self.verifications.insert_one(verification)
        _report = self.reports.find_one({'shortLink': verification['shortLink']})
        self.bot.client.api.channels_messages_modify(
            event.msg.channel_id,
            _report.get('message_id'),
            embed=self.create_card_embed(_report)
        )

        _trellostring = _trellostring = "Can reproduce.\n" + verification.get('reason') + '\n\n' + verification.get('name')
        self.trello_client.add_comment(verification.get('shortLink'), _trellostring)

        tally = {}
        tally['approve'] = self.tally_approvals(verification)
        tally['deny'] = self.tally_denials(verification)
        if tally['approve'] >= self.config.verification_threshold:
            report_board = self.trello_client.get_card(_report.get('shortLink')).get('idBoard')
            self.trello_client.to_list(_report.get('shortLink'), self.config.fixed_dict.get(report_board).get('fix'))
            rplymsg = event.msg.reply('Moving to Verified Fixed!')
            rplymsg.delete()
            self.bot.client.api.channels_messages_delete(
                event.msg.channel_id,
                _report.get('message_id')
            )

        if tally['deny'] >= self.config.verification_threshold:
            report_board = self.trello_client.get_card(_report.get('shortLink')).get('idBoard')
            self.trello_client.to_list(_report.get('shortLink'), self.config.fixed_dict.get(report_board).get('ver'))
            rplymsg = event.msg.reply("Moving back to Verified Bugs!")
            rplymsg.delete()
            self.bot.client.api.channels_messages_delete(
                event.msg.channel_id,
                _report.get('message_id')
            )

        self.shared_handle_action(verification['user_id'], "verify", True)

        event.msg.delete()

    def tally_approvals(self, verification):
        pipeline = [
            {'$match': {'shortLink': verification.get('shortLink'), 'stance': 'approve'}},
            {'$count': 'num_verified'}
        ]
        verif_dict = list(self.verifications.aggregate(pipeline))
        if not verif_dict:
            return 0
        return verif_dict[0].get('num_verified')

    def tally_denials(self, verification):
        pipeline = [
            {'$match': {'shortLink': verification.get('shortLink'), 'stance': 'deny'}},
            {'$count': 'num_verified'}
        ]
        verif_dict = list(self.verifications.aggregate(pipeline))
        if not verif_dict:
            return 0
        return verif_dict[0].get('num_verified')

    @BasePlugin.route('/webhook', methods=['POST', 'GET'])
    def handle_webhook(self):
        from flask import request

        data = request.get_json()

        if not data:
            return '', 200

        action = data.get("action")

        if not action:
            return '', 200

        action_info = action.get('data')

        # replace with something more general
        if not action_info:
            return '', 200

        if not action_info.get('listAfter'):
            return '', 200

        list_info = action_info.get('listAfter')

        if list_info.get('id') not in self.config.fixed_list:
            return '', 200

        card_info = action_info.get('card')

        if not self.reports.find_one({'shortLink': card_info.get('shortLink')}):
            card_resp = self.trello_client.get_card(card_info.get('shortLink'))
            card_desc = card_resp.get('desc')
            card_board = card_resp.get("idBoard")
            card_id_match = re.search(".*$", card_desc)
            card_id = card_id_match.group(0)
            _report = {
                '_id': card_id,
                'name': card_info.get('name'),
                'shortLink': card_info.get('shortLink'),
                'board': card_board
            }
            self.reports.insert_one(
                _report
            )
        _queue_message = self.bot.client.api.channels_messages_create(
            self.config.fixed_queue,
            embed=self.create_card_embed(_report)
            )
        self.reports.update_one(
            {
                'shortLink': card_info.get('shortLink'),
            }, {
                    '$set': {'message_id': str(_queue_message.id)}
                }
        )
        return '', 200

    def get_card_info(self, card):
        card_link = card.get('shortLink')
        card_desc = self.trello_client.get_card(card_link).get('desc')
        return self.info_parse(card_desc)

    def info_parse(self, info):
        info = info.replace("####Steps to reproduce:", "**Steps to reproduce:**")
        info = info.replace("####Expected result:", "**Expected result:**")
        info = info.replace("####Actual result:", "**Actual result:**")
        info = info.replace("####Client settings:", "**Client settings:**")
        info = info.replace("####System settings:", "**System settings:**")
        return info

    def create_card_embed(self, card):
        if not card:
            return
        embed = MessageEmbed()
        embed.title = card.get('name')
        card_url = 'https://trello.com/c/' + card.get('shortLink')
        board_emoji = self.config.board_to_emoji.get(card.get('board'))
        if not self.verifications.find_one({'shortLink': card.get('shortLink')}):
            embed.description = "**Board:**" + board_emoji + '\n' + self.get_card_info(card) + '\nLink: ' + card_url
        else:
            embed.description = "**Board:**" + board_emoji + '\n' + self.get_card_info(card) + '\nLink: ' + card_url + '\n\n**Reproducibility:**'
            cursor = self.verifications.find({'shortLink': card.get('shortLink')})
            for verification in cursor:
                if verification.get('stance') == 'approve':
                    embed.description = embed.description + (
                        '\n<:greentick:326519582657609728> ' + verification.get('name') + ' | `' + verification.get('reason') + '`'
                        )
                if verification.get('stance') == 'deny':
                    embed.description = embed.description + (
                        '\n<:redTick:312314733816709120> ' + verification.get('name') + ' | `' + verification.get('reason') + '`'
                        )
        embed.color = int(0xe74c3c)
        return embed
