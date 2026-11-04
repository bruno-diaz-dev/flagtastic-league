"""Approved points-for credits must not create results or penalize opponents."""

from fastapi.testclient import TestClient
import pytest

from database import get_connection
from main import app
from repositories.statistics import get_game_statistics
from services import standings_adjustments as policy

client = TestClient(app)


@pytest.fixture(autouse=True)
def empty_games():
    with get_connection() as connection:
        connection.execute('DELETE FROM teams')
        connection.execute('DELETE FROM players WHERE curp=%s', ('RETAINTEST00000001',))


def fixture(monkeypatch):
    home, away = [client.post('/api/teams',json={
        'name':name,'branch':'mixto','category':'u12'
    }).json()['id'] for name in ('Credit home','Credit away')]
    game = client.post('/api/games',json={
        'home_team_id':home,'away_team_id':away,'week':4,'field_number':4,'start_time':'16:00'
    }).json()
    assert client.patch(f"/api/games/{game['id']}/score",json={'home_score':0,'away_score':42}).status_code==200
    monkeypatch.setattr(policy,'POINTS_FOR_ADJUSTMENTS', ({
        'source_game_id':game['id'],'home_team_id':home,'away_team_id':away,'week':4,
        'home_score':0,'away_score':42,'team_id':away,'team_name':'Credit away','category':'u12','points_for':42
    },))
    return game, home, away


def standings():
    return {r['team_id']:r for r in client.get('/api/standings?branch=mixto&category=u12').json()}


def test_removed_result_keeps_only_winner_points_without_affecting_opponent(monkeypatch):
    game, home, away = fixture(monkeypatch)
    # Existing source means normal totals; no extra credit.
    before = standings()
    assert (before[away]['wins'],before[away]['points_for']) == (1,42)
    with get_connection() as connection:
        player=connection.execute("INSERT INTO players(name,curp,age) VALUES ('Retained Player','RETAINTEST00000001',20) RETURNING id").fetchone()['id']
        connection.execute('INSERT INTO player_week_stats(week,game_id,team_id,player_id,points,receptions) VALUES(4,%s,%s,%s,6,2)',(game['id'],away,player))
    assert client.delete(f"/api/games/{game['id']}").status_code==204
    result=standings()
    loser, winner=result[home],result[away]
    assert (loser['games_played'],loser['wins'],loser['losses'],loser['points_for'],loser['points_against'],loser['point_difference']) == (0,0,0,0,0,0)
    assert (winner['games_played'],winner['wins'],winner['losses'],winner['points_for'],winner['points_against'],winner['point_difference']) == (0,0,0,42,0,42)
    assert standings()==result
    assert client.get('/api/games').json()==[]
    assert get_game_statistics(game['id'])==[]
    with get_connection() as connection:
        stats=connection.execute('SELECT game_id,points,receptions FROM player_week_stats WHERE player_id=%s',(player,)).fetchone()
        assert dict(stats)=={'game_id':None,'points':6,'receptions':2}


@pytest.mark.parametrize('reverse',[False,True])
def test_completed_replacement_cannot_double_credit_the_same_result(monkeypatch, reverse):
    game, home, away=fixture(monkeypatch)
    assert client.delete(f"/api/games/{game['id']}").status_code==204
    replacement=client.post('/api/games',json={'home_team_id':away if reverse else home,'away_team_id':home if reverse else away,'week':4,'field_number':1}).json()
    assert client.patch(f"/api/games/{replacement['id']}/score",json={'home_score':42 if reverse else 0,'away_score':0 if reverse else 42}).status_code==200
    rows=standings()
    assert rows[away]['points_for']==42 and rows[away]['wins']==1
    # Reimporting a match uses its ordinary result; the adjustment doesn't rewrite it.
    assert rows[home]['points_against']==42 and rows[home]['losses']==1


def test_other_divisions_and_other_games_keep_their_normal_behavior(monkeypatch):
    game, home, away=fixture(monkeypatch)
    assert client.delete(f"/api/games/{game['id']}").status_code==204
    other=client.post('/api/games',json={'home_team_id':home,'away_team_id':away,'week':5,'field_number':1}).json()
    assert client.patch(f"/api/games/{other['id']}/score",json={'home_score':6,'away_score':12}).status_code==200
    result=standings()
    assert (result[away]['points_for'],result[away]['points_against'],result[away]['wins'],result[away]['games_played'])==(54,6,1,1)
    assert (result[home]['points_for'],result[home]['points_against'],result[home]['losses'])==(6,12,1)
    with get_connection() as connection:
        connection.execute("UPDATE teams SET category='u14' WHERE id=ANY(%s)",([home,away],))
    u14={r['team_id']:r for r in client.get('/api/standings?branch=mixto&category=u14').json()}
    assert u14[away]['points_for']==12
    assert client.delete(f"/api/games/{other['id']}").status_code==204
    assert next(r for r in client.get('/api/standings?branch=mixto&category=u14').json() if r['team_id']==away)['points_for']==0


def test_team_identity_must_still_match_the_approved_credit(monkeypatch):
    game, home, away=fixture(monkeypatch)
    assert client.delete(f"/api/games/{game['id']}").status_code==204
    with get_connection() as connection:
        connection.execute("UPDATE teams SET name='Different team' WHERE id=%s",(away,))
    assert standings()[away]['points_for']==0
