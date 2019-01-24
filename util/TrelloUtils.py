# coding=utf-8
import json

import requests

card_cache = dict()
board_cache = dict()
list_cache = dict()


def getCardInfo(event, id):
    if id.startswith("https"):
        id = extractID(event, id)
    if id is None:
        return False
    if not id in list_cache.keys():
        response = requests.request("GET", "https://api.trello.com/1/cards/{}".format(id))
        try:
            card_cache[id] = json.loads(response.text)
        except ValueError as ex:
            return None
    return card_cache[id]


def getBoardInfo(id):
    if id not in board_cache.keys():
        response = requests.request("GET", "https://api.trello.com/1/boards/{}".format(id))
        board_cache[id] = json.loads(response.text)
    return board_cache[id]


def getListInfo(id):
    if id not in list_cache.keys():
        response = requests.request("GET", "https://api.trello.com/1/lists/{}".format(id))
        list_cache[id] = json.loads(response.text)
    return list_cache[id]


def extractID(event, link):
    # verify link
    if not link.lower().startswith("https://trello.com/c/"):
        event.channel.send_message("This is not the type of link I was looking for 😐").after(10).delete()
        return None
    if len(link) <= 21:
        event.channel.send_message("please include a valid trello url").after(10).delete()
        return None
    trello_id = link.split("https://trello.com/c/")[1].split("/")[0]
    if trello_id.endswith(" "):
        trello_id = trello_id[:-1]
    return trello_id
