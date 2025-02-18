import json

# Simulated OSRS item data
TEST_ITEMS = [
    {
        "id": 1,
        "name": "Abyssal whip",
        "high_alch": 60000,
        "low_alch": 40000,
        "current_price": 2500000,
        "high_vol": 100,
        "low_vol": 50,
        "high_price": 2600000,
        "low_price": 2400000,
        "image": "https://oldschool.runescape.wiki/images/thumb/Abyssal_whip_detail.png/1200px-Abyssal_whip_detail.png?d4bb6",
    },
    {
        "id": 2,
        "name": "Dragon scimitar",
        "high_alch": 50000,
        "low_alch": 30000,
        "current_price": 100000,
        "high_vol": 200,
        "low_vol": 150,
        "high_price": 120000,
        "low_price": 90000,
        "image": "https://oldschool.runescape.wiki/images/thumb/Dragon_scimitar_detail.png/1200px-Dragon_scimitar_detail.png?4b4b6",
    },
    # Add more items as needed
]

# Skill names corresponding to the positions in the API response
SKILL_NAMES = [
    "Overall",
    "Attack",
    "Defence",
    "Strength",
    "Hitpoints",
    "Ranged",
    "Prayer",
    "Magic",
    "Cooking",
    "Woodcutting",
    "Fletching",
    "Fishing",
    "Firemaking",
    "Crafting",
    "Smithing",
    "Mining",
    "Herblore",
    "Agility",
    "Thieving",
    "Slayer",
    "Farming",
    "Runecrafting",
    "Hunter",
    "Construction",
]

STORAGE_BUCKET="osrs-trading-app.appspot.com"
ALLOWED_SERVER_IDS = [1257148959902666783, 1109908777244831764, 683885593448546316]
ALLOWED_CHANNEL_IDS = [1259221807832236142, 1259005486343389265, 1109908970929393695, 683885593452740738]