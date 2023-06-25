import requests
from datetime import datetime, timedelta


class ChessDotComService:
    def __init__(self):
        pass

    @staticmethod
    def build():
        return ChessDotComService()

    def get_games_by_username(self, username, get_pgns=False, limit=1000):
        archives_url = f'https://api.chess.com/pub/player/{username}/games/archives'
        archives = self.get_archives(archives_url)[::-1]
        games = []
        for archive in archives:
            ith_games = self.__get_games(archive, username.lower(), get_pgns)
            games.extend(ith_games)
            if len(games) >= limit:
                break
        return games

    def __get_games(self, archive_url, username='tobiahsrex', get_pgns=False):
        try:
            response = requests.get(archive_url)
            response.raise_for_status()
            data = response.json()
            games_result = []
            if data:
                for game in data.get('games', []):
                    if get_pgns:
                        games_result.append(game['pgn'])
                        continue
                    is_white = game['white']['username'].lower() == username
                    my_win = game['white']['result'] == 'win' if is_white else game['black']['result'] == 'win'
                    meta_data = game['pgn'].split('\n')
                    date = next(line[7:17]
                                for line in meta_data if line.startswith('[Date'))
                    start_time = next(
                        line[12:20] for line in meta_data if line.startswith('[StartTime'))
                    end_time = next(
                        line[10:18] for line in meta_data if line.startswith('[EndTime'))
                    start_time, end_time = self.parse_time(
                        start_time, end_time, date)
                    opponent_id = game.get('black', {}).get(
                        '@id') if is_white else game.get('white', {}).get('@id')
                    opponent_profile = self.get_profile(opponent_id)
                    template = {
                        'username': username,
                        'avatar': 'https://images.chesscomfiles.com/uploads/v1/user/92675886.c4235591.200x200o.d93954e125ad.jpeg',
                        'name': opponent_profile.get('name', ''),
                        'url': opponent_profile.get('url', ''),
                        'location': 'San Francisco, CA',
                    }
                    result = {
                        'white': {
                            **game.get('white', ''),
                            'avatar': template.get('avatar', '') if is_white else opponent_profile.get('avatar', '')
                        },
                        'black': {
                            **game.get('black', ''),
                            'avatar': opponent_profile.get('avatar', '') if is_white else template.get('avatar', ''),
                        },
                        'time_class': game.get('time_class', ''),
                        'time_control': f"{int(game.get('time_control', '').split('+')[0]) / 60} min",
                        'start_time': start_time,
                        'end_time': end_time,
                        'my_color': 'white' if is_white else 'black',
                        'my_rating': game.get('white', {}).get('rating', 0) if is_white else game.get('black', {}).get('rating', 0),
                        'result': 'win' if my_win else 'loss' if not my_win else 'draw',
                        'link': game.get('url', ''),
                        'pgn': game.get('pgn', ''),
                        'url': game.get('url', ''),
                    }
                    games_result.append(result)
            return games_result
        except requests.exceptions.RequestException as error:
            print('Error fetching games:', error)
            return []

    def parse_time(self, start_time, end_time, date):
        start = datetime.strptime(f"{date} {start_time}", "%Y.%m.%d %H:%M:%S")
        end = datetime.strptime(f"{date} {end_time}", "%Y.%m.%d %H:%M:%S")
        dt_pst = datetime(start.year, start.month, start.day,
                          end.hour, end.minute, end.second) - timedelta(hours=8)
        end_time = dt_pst.strftime("%Y.%m.%d %H:%M:%S")
        duration = end - start
        start_dt = dt_pst - duration
        start_time = start_dt.strftime("%Y.%m.%d %H:%M:%S")
        return start_time, end_time

    def get_profile(self, profile_url):
        try:
            response = requests.get(profile_url)
            response.raise_for_status()
            data = response.json()
            return {
                'username': data.get('username', ''),
                'avatar': data.get('avatar', 'https://e7.pngegg.com/pngimages/980/304/png-clipart-computer-icons-user-profile-avatar-heroes-silhouette-thumbnail.png'),
                'name': data.get('name', ''),
                'url': data.get('url', ''),
                'location': data.get('location', ''),
            }
        except requests.exceptions.RequestException as error:
            print('Error fetching profile:', error)
            return []

    def get_archives(self, archives_url):
        try:
            response = requests.get(archives_url)
            response.raise_for_status()
            data = response.json()
            return data['archives']
        except requests.exceptions.RequestException as error:
            print('Error fetching archives:', error)
            return []


if __name__ == '__main__':
    chess_dot_com = ChessDotComService()
    games = chess_dot_com.get_games_by_username('MagnusCarlsen', get_pgns=True)
    print(len(games))
