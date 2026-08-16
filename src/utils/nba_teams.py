import enum
from dataclasses import dataclass


class NbaTeam(enum.Enum):
    CELTICS = enum.auto()
    BULLS = enum.auto()
    HAWKS = enum.auto()
    NETS = enum.auto()
    CAVALIERS = enum.auto()
    HORNETS = enum.auto()
    KNICKS = enum.auto()
    PISTONS = enum.auto()
    HEAT = enum.auto()
    SIXERS = enum.auto()
    PACERS = enum.auto()
    MAGIC = enum.auto()
    RAPTORS = enum.auto()
    BUCKS = enum.auto()
    WIZARDS = enum.auto()
    NUGGETS = enum.auto()
    WARRIORS = enum.auto()
    MAVERICKS = enum.auto()
    TIMBERWOLVES = enum.auto()
    CLIPPERS = enum.auto()
    ROCKETS = enum.auto()
    THUNDER = enum.auto()
    LAKERS = enum.auto()
    GRIZZLIES = enum.auto()
    TRAIL_BLAZERS = enum.auto()
    SUNS = enum.auto()
    PELICANS = enum.auto()
    JAZZ = enum.auto()
    KINGS = enum.auto()
    SPURS = enum.auto()


class NbaConference(enum.Enum):
    WEST = enum.auto()
    EAST = enum.auto()


class NbaDivision(enum.Enum):
    ATLANTIC = enum.auto()
    CENTRAL = enum.auto()
    SOUTHEAST = enum.auto()
    NORTHWEST = enum.auto()
    PACIFIC = enum.auto()
    SOUTHWEST = enum.auto()


@dataclass
class TeamDetails:
    full_name: str
    short_name: str
    location_name: str
    conference: NbaConference
    division: NbaDivision
    abbreviation: str
    other_names: list[str]


_NBA_TEAMS: dict[NbaTeam, TeamDetails] = {
    NbaTeam.CELTICS: TeamDetails('Boston Celtics', 'Celtics', 'Boston', NbaConference.EAST, NbaDivision.ATLANTIC, 'BOS', []),
    NbaTeam.NETS: TeamDetails('Brooklyn Nets', 'Nets', 'Brooklyn', NbaConference.EAST, NbaDivision.ATLANTIC, 'BKN', []),
    NbaTeam.KNICKS: TeamDetails('New York Knicks', 'Knicks', 'New York', NbaConference.EAST, NbaDivision.ATLANTIC, 'NYK', ['Knickerbockers', 'New York Knickerbockers', 'NY', 'NYC']),
    NbaTeam.SIXERS: TeamDetails('Philadelphia 76ers', '76ers', 'Philadelphia', NbaConference.EAST, NbaDivision.ATLANTIC, 'PHI' ['Seventy-Sixers', 'Seventy Sixers', 'Philadelphia Seventy-Sixers', 'Philadelphia Seventy Sixers', 'Philly', 'Sixers', '6ers']),
    NbaTeam.RAPTORS: TeamDetails('Toronto Raptors', 'Raptors', 'Toronto', NbaConference.EAST, NbaDivision.ATLANTIC, 'TOR', ['Raps']),
    NbaTeam.BULLS: TeamDetails('Chicago Bulls', 'Bulls', 'Chicago', NbaConference.EAST, NbaDivision.CENTRAL, 'CHI', ['Chitown', 'Chi-Town']),
    NbaTeam.CAVALIERS: TeamDetails('Cleaveland Cavaliers', 'Cavaliers', 'Cleaveland', NbaConference.EAST, NbaDivision.CENTRAL, 'CLE', ['Cavs', 'Cleaveland Cavs']),
    NbaTeam.PISTONS: TeamDetails('Detroit Pistons', 'Pistons', 'Detroit', NbaConference.EAST, NbaDivision.CENTRAL, 'DET', ['Detroit Basketball']),
    NbaTeam.PACERS: TeamDetails('Indiana Pacers', 'Pacers', 'Indiana', NbaConference.EAST, NbaDivision.CENTRAL, 'IND', ['Indy', 'Indy Pacers']),
    NbaTeam.BUCKS: TeamDetails('Milwaukee Bucks', 'Bucks', 'Milwaukee', NbaConference.EAST, NbaDivision.CENTRAL, 'MIL', []),
    NbaTeam.HAWKS: TeamDetails('Atlanta Hawks', 'Hawks', 'Atlanta', NbaConference.EAST, NbaDivision.SOUTHEAST, 'ATL', []),
    NbaTeam.HORNETS: TeamDetails('Charlotte Hornets', 'Hornets', 'Charlotte', NbaConference.EAST, NbaDivision.SOUTHEAST, 'CHA', []),
    NbaTeam.HEAT: TeamDetails('Miami Heat', 'Heat', 'Miami', NbaConference.EAST, NbaDivision.SOUTHEAST, 'MIA', []),
    NbaTeam.MAGIC: TeamDetails('Orlando Magic', 'Magic', 'Orlando', NbaConference.EAST, NbaDivision.SOUTHEAST, 'ORL', []),
    NbaTeam.WIZARDS: TeamDetails('Washington Wizards', 'Wizards', 'Washington', NbaConference.EAST, NbaDivision.SOUTHEAST, 'WAS', []),
    NbaTeam.NUGGETS: TeamDetails('Denver Nuggets', 'Nuggets', 'Denver', NbaConference.WEST, NbaDivision.NORTHWEST, 'DEN', ['Nuggs', 'Nugs', 'Denver Nuggs', 'Denver Nugs']),
    NbaTeam.TIMBERWOLVES: TeamDetails('Minnesota Timberwolves', 'Timberwolves', 'Minnesota', NbaConference.WEST, NbaDivision.NORTHWEST, 'MIN', ['Wolves', 'Minnesota Wolves']),
    NbaTeam.THUNDER: TeamDetails('Oklahoma City Thunder', 'Thunder', 'Oklahoma City', NbaConference.WEST, NbaDivision.NORTHWEST, 'OKC', ['Oklahoma', 'Oklahoma Thunder', 'OKC', 'OKC Thunder']),
    NbaTeam.TRAIL_BLAZERS: TeamDetails('Portland Trail Blazers', 'Trail Blazers', 'Portland', NbaConference.WEST, NbaDivision.NORTHWEST, 'POR', ['Blazers', 'Portland Blazers', 'Trailblazers', 'Portland Trailblazers']),
    NbaTeam.JAZZ: TeamDetails('Utah Jazz', 'Jazz', 'Utah', NbaConference.WEST, NbaDivision.NORTHWEST, 'UTA', []),
    NbaTeam.WARRIORS: TeamDetails('Golden State Warriors', 'Warriors', 'Golden State', NbaConference.WEST, NbaDivision.PACIFIC, 'GSW', ['Dubs', 'Golden State Dubs', 'San Francisco']),
    NbaTeam.CLIPPERS: TeamDetails('LA Clippers', 'Clippers', 'LA', NbaConference.WEST, NbaDivision.PACIFIC, 'LAC', ['Clips', 'LA Clips', 'Los Angeles Clippers', 'Los Angeles Clips']),
    NbaTeam.LAKERS: TeamDetails('Los Angeles Lakers', 'Lakers', 'Los Angeles', NbaConference.WEST, NbaDivision.PACIFIC, 'LAL', ['LA Lakers']),
    NbaTeam.SUNS: TeamDetails('Phoenix Suns', 'Suns', 'Phoenix', NbaConference.WEST, NbaDivision.PACIFIC, 'PHX', []),
    NbaTeam.KINGS: TeamDetails('Sacramento Kings', 'Kings', 'Sacramento', NbaConference.WEST, NbaDivision.PACIFIC, 'SAC', ['Sactown', 'Sactown Kings']),
    NbaTeam.MAVERICKS: TeamDetails('Dallas Mavericks', 'Mavericks', 'Dallas', NbaConference.WEST, NbaDivision.SOUTHWEST, 'DAL', ['Mavs', 'Dallas Mavs']),
    NbaTeam.ROCKETS: TeamDetails('Houston Rockets', 'Rockets', 'Houston', NbaConference.WEST, NbaDivision.SOUTHWEST, 'HOU', []),
    NbaTeam.GRIZZLIES: TeamDetails('Memphis Grizzlies', 'Grizzlies', 'Memphis', NbaConference.WEST, NbaDivision.SOUTHWEST, 'MEM', ['Grizz', 'Griz', 'Memphis Grizz', 'Memphis Griz']),
    NbaTeam.PELICANS: TeamDetails('New Orleans Pelicans', 'Pelicans', 'New Orleans', NbaConference.WEST, NbaDivision.SOUTHWEST, 'NOP', ['Pels', 'New Orleans Pels']),
    NbaTeam.SPURS: TeamDetails('San Antonio Spurs', 'Spurs', 'San Antonio', NbaConference.WEST, NbaDivision.SOUTHWEST, 'SAS', []),
}


_STR_TO_TEAM = {}
for team, details in _NBA_TEAMS.items():
    _STR_TO_TEAM[details.full_name.lower()] = team
    _STR_TO_TEAM[details.short_name.lower()] = team
    _STR_TO_TEAM[details.abbreviation.lower()] = team
    _STR_TO_TEAM[details.location_name.lower()] = team
    for other_name in details.other_names:
        _STR_TO_TEAM[other_name.lower()] = team


def look_up_team(query: str) -> tuple[NbaTeam, TeamDetails]:
    return _STR_TO_TEAM[query.lower()], _NBA_TEAMS[_STR_TO_TEAM[query.lower()]]
