"""Friendly fixtures accept guests without changing competition totals."""
import pytest
from fastapi.testclient import TestClient
from database import get_connection
from main import app

client = TestClient(app)

@pytest.fixture(autouse=True)
def clean_database():
    with get_connection() as connection:
        connection.execute('DELETE FROM team_players')
        connection.execute('DELETE FROM players')
        connection.execute('DELETE FROM teams')


def league_team(name):
    return client.post('/api/teams', json={'name':name,'branch':'mixto','category':'libre'}).json()['id']

def fixture(**kwargs):
    return {'is_friendly':True,'home_guest_name':'Invitados A','away_guest_name':'Invitados B',
            'branch':'mixto','category':'libre','week':1,'field_number':1,'start_time':'10:00',**kwargs}

def test_friendly_guests_are_public_but_not_league_teams_or_standings():
    response = client.post('/api/games', json=fixture())
    assert response.status_code == 201
    game = response.json()
    assert game['is_friendly'] is True
    listed = next(g for g in client.get('/api/games').json() if g['id'] == game['id'])
    assert listed['home_team']['name'] == 'Invitados A'
    assert listed['home_team']['is_guest'] is True
    assert client.get('/api/teams').json() == []
    assert client.get('/api/standings?branch=mixto&category=libre').json() == []
    assert client.get(f"/api/games/{game['id']}/details").json()['game']['is_friendly'] is True

def test_friendlies_do_not_change_played_games_or_points():
    a,b = league_team('Oficial A'),league_team('Oficial B')
    official = client.post('/api/games',json={'home_team_id':a,'away_team_id':b,'week':1,'field_number':1}).json()['id']
    friendly = client.post('/api/games',json=fixture(home_team_id=a,home_guest_name=None)).json()['id']
    for game, score in [(official,{'home_score':7,'away_score':6}),(friendly,{'home_score':99,'away_score':1})]:
        assert client.patch(f'/api/games/{game}/score',json=score).status_code == 200
    rows = client.get('/api/standings?branch=mixto&category=libre').json()
    row = next(r for r in rows if r['team_id']==a)
    assert row['games_played']==1 and row['wins']==1 and row['points_for']==7
    assert len(rows)==2

def test_guests_require_friendly_and_a_division():
    assert client.post('/api/games',json=fixture(is_friendly=False)).status_code == 422
    assert client.post('/api/games',json=fixture(branch=None)).status_code == 422
    assert client.post('/api/games',json=fixture(home_guest_name='  ')).status_code == 422
    assert client.post('/api/games',json=fixture(away_guest_name=' invitados a ')).status_code == 409
    assert client.get('/api/games').json()==[]
    with get_connection() as connection:
        assert connection.execute('SELECT COUNT(*) AS n FROM teams').fetchone()['n']==0

def test_import_friendlies_is_idempotent_and_reuses_invited_identity():
    payload={'games':[fixture()]}
    first=client.post('/api/games/schedule/confirm',json=payload)
    assert first.status_code==200 and first.json()['created']==1
    second=client.post('/api/games/schedule/confirm',json=payload)
    assert second.status_code==200 and second.json()['skipped']==1
    with get_connection() as connection:
        assert connection.execute('SELECT COUNT(*) AS n FROM teams WHERE is_guest').fetchone()['n']==2

def test_import_conflict_rolls_back_guests_and_keeps_scored_game():
    game=client.post('/api/games',json=fixture()).json()['id']
    assert client.patch(f'/api/games/{game}/score',json={'home_score':6,'away_score':0}).status_code==200
    response=client.post('/api/games/schedule/confirm',json={'games':[fixture(home_guest_name='Nuevo invitado')]})
    assert response.status_code==409
    with get_connection() as connection:
        assert connection.execute("SELECT 1 FROM teams WHERE name='Nuevo invitado'").fetchone() is None
        assert connection.execute('SELECT home_score FROM games WHERE id=%s',(game,)).fetchone()['home_score']==6

def test_guest_id_cannot_be_used_in_official_fixture():
    game=client.post('/api/games',json=fixture()).json()
    response=client.post('/api/games',json={'home_team_id':game['home_team_id'],'away_team_id':game['away_team_id'],'field_number':1})
    assert response.status_code==409


def test_live_friendly_keeps_match_statistics_out_of_season_and_finals():
    from uuid import uuid4
    from models import UserCreate
    from repositories.users import create_user
    from repositories.live_games import start_live_game, append_event, read_live_game, finish_live_game
    home,away=league_team('Captura A'),league_team('Captura B')
    player=client.post(f'/api/teams/{home}/players',json={'name':'Jugador amistoso','curp':uuid4().hex[:18].upper(),'age':25,'jersey_number':1}).json()['id']
    official=client.post('/api/games',json={'home_team_id':home,'away_team_id':away,'field_number':2}).json()['id']
    friendly=client.post('/api/games',json=fixture(home_team_id=home,away_team_id=away,home_guest_name=None,away_guest_name=None)).json()['id']
    user=create_user(UserCreate(name='Capturista',email=f'friendly-{uuid4().hex}@example.test',password='supersecret',role='referee'))['id']
    start_live_game(friendly,user)
    for kind in ('attendance','touchdown'):
        append_event(friendly,{'client_id':uuid4(),'kind':kind,'team_id':home,'player_id':player,'receiver_id':None,'period':1,'minute':1,'second':0,'note':''},user)
    live=read_live_game(friendly)
    assert live['is_friendly'] is True
    assert live['home_score']==6 and live['statistics'][0]['points']==6
    finish_live_game(friendly,live['version'],user)
    attendance=next(r for r in read_live_game(official)['attendance'] if r['player_id']==player)
    assert attendance['scheduled_games']==1 and attendance['attended_games']==0
    with get_connection() as connection:
        assert connection.execute('SELECT COUNT(*) AS n FROM player_week_stats WHERE game_id=%s',(friendly,)).fetchone()['n']==0
    leaders=client.get('/api/statistics/leaderboards?branch=mixto&category=libre').json()
    assert all(not rows for rows in leaders.values())
