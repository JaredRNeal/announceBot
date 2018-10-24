import json


def fetchFromDisk(filename):
    try:
        with open(filename + ".json") as file:
            return json.load(file)
    except EnvironmentError:
        return dict()

def saveToDisk(filename, dict):
    with open(filename + ".json", "w") as file:
        json.dump(dict, file, indent=4, skipkeys=True, sort_keys=True)

def trim_message(message, limit):
    if len(message) < limit - 3:
        return message
    return message[:limit-1] + "..."