import requests

def fetch_player_stats(username, skill_names):
    url = f"https://secure.runescape.com/m=hiscore_oldschool/index_lite.ws?player={username}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.text.splitlines()
        stats = {}
        for index, line in enumerate(data):
            values = line.split(",")
            if index < len(skill_names):
                stats[skill_names[index]] = {
                    "rank": values[0],
                    "level": values[1],
                    "experience": values[2],
                }
        return stats
    else:
        return None