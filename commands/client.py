from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import requests


class TrelloClient(object):

    def __init__(self, key, token):
        self._token = token
        self._key = key
        self.retry = Retry(
            total=3,
            status_forcelist=[],
            backoff_factor=1
        )
        self.adapter = HTTPAdapter(max_retries=self.retry)
        self.session = requests.Session()
        self.session.mount('https://api.trello.com/1/cards/', self.adapter)

    @property
    def params(self):
        return dict(key=self._key, token=self._token)

    def get_card(self, card):
        params = self.params
        resp = self.session.get('https://api.trello.com/1/cards/{}'.format(card), params=params)
        return resp.json()

    def to_list(self, card, _list):
        params = self.params
        params.update({'idList': _list})
        self.session.put('https://api.trello.com/1/cards/{}'.format(card), params=params)

    def add_member(self, card, _member):
        params = self.params
        get_resp = self.session.get('https://api.trello.com/1/cards/{}'.format(card), params=params).json()
        if not get_resp.get('idMembers'):
            mem_ids = []
            mem_ids.append(_member)
        else:
            mem_ids = get_resp.get('idMembers').append(_member)
        params.update({'idMembers': mem_ids})
        self.session.put('https://api.trello.com/1/cards/{}'.format(card), params=params)

    def remove_member(self, card, _member):
        params = self.params
        get_resp = self.session.get('https://api.trello.com/1/cards/{}'.format(card), params=params).json()
        if not get_resp.get('idMembers'):
            return
        else:
            self.session.delete('https://api.trello.com/1/cards/{}/idMembers/{}'.format(card, _member), params=params)
