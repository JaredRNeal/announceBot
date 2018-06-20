import requests
import json

board_cache = dict()
list_cache = dict()

def getCardInfo(event, id):
    if id.startswith("https"):
        id = extractID(event, id)
    if id is None:
        return None
    response = requests.request("GET", "https://api.trello.com/1/cards/{}".format(id))
    try:
        return json.loads(response.text)
    except json.JSONDecodeError as ex:
        return None

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
        event.channel.send_message("This is not the type of link i was looking for 😐").after(10).delete()
        return None
    if len(link) <= 21:
        event.channel.send_message("please include a valid trello url").after(10).delete()
        return None

    # check to see if it's already reported
    return link.split("https://trello.com/c/")[1].split("/")[0]