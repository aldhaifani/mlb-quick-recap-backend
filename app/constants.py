from enum import Enum


class GameType(str, Enum):
    REGULAR = "R"
    POSTSEASON = "P"
    SPRING = "S"


class Sport(Enum):
    MLB = 1


# MLB Team IDs
MLB_TEAMS = {
    "ARI": 109,  # Arizona Diamondbacks
    "ATL": 144,  # Atlanta Braves
    "BAL": 110,  # Baltimore Orioles
    "BOS": 111,  # Boston Red Sox
    "CHC": 112,  # Chicago Cubs
    "CWS": 145,  # Chicago White Sox
    "CIN": 113,  # Cincinnati Reds
    "CLE": 114,  # Cleveland Guardians
    "COL": 115,  # Colorado Rockies
    "DET": 116,  # Detroit Tigers
    "HOU": 117,  # Houston Astros
    "KC": 118,  # Kansas City Royals
    "LAA": 108,  # Los Angeles Angels
    "LAD": 119,  # Los Angeles Dodgers
    "MIA": 146,  # Miami Marlins
    "MIL": 158,  # Milwaukee Brewers
    "MIN": 142,  # Minnesota Twins
    "NYM": 121,  # New York Mets
    "NYY": 147,  # New York Yankees
    "OAK": 133,  # Oakland Athletics
    "PHI": 143,  # Philadelphia Phillies
    "PIT": 134,  # Pittsburgh Pirates
    "SD": 135,  # San Diego Padres
    "SF": 137,  # San Francisco Giants
    "SEA": 136,  # Seattle Mariners
    "STL": 138,  # St. Louis Cardinals
    "TB": 139,  # Tampa Bay Rays
    "TEX": 140,  # Texas Rangers
    "TOR": 141,  # Toronto Blue Jays
    "WSH": 120,  # Washington Nationals
}

MLB_DATE_FORMAT = "YYYY/MM/DD"
CACHE_EXPIRATION = 600  # 10 minutes in seconds
GAMES_PER_PAGE = 10
