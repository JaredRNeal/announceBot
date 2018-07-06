import json


def fetchFromDisk(filename):
    try:
        with open(f"{filename}.json") as file:
            return json.load(file)
    except FileNotFoundError:
        return dict()

def saveToDisk(filename, dict):
    with open(f"{filename}.json", "w") as file:
        json.dump(dict, file, indent=4, skipkeys=True, sort_keys=True)

def trim_message(message, limit):
    if len(message) < limit - 3:
        return message
    return f"{message[:limit-1]}..."