"""Only stored friendly games may omit the two core referee positions."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from database import get_connection
from dependencies.auth import require_league_admin
from main import app
from models import UserCreate
from repositories.users import create_user

client = TestClient(app)


@pytest.fixture
def crew():
    with get_connection() as connection:
        connection.execute('DELETE FROM teams')
    users = [create_user(UserCreate(email=f'friendly-crew-{uuid4().hex}@example.test',
              name=f'Friendly official {index}',password='supersecret',role='referee')) for index in range(3)]
    app.dependency_overrides[require_league_admin] = lambda: {**users[0], 'role':'league_admin'}
    teams = [client.post('/api/teams',json={'name':name,'branch':'mixto','category':'libre'}).json()['id']
             for name in ('Friendly local','Friendly visitante')]
    def game(friendly):
        return client.post('/api/games',json={'home_team_id':teams[0],'away_team_id':teams[1],
            'week':5,'field_number':2 if friendly else 1,'start_time':'12:00','is_friendly':friendly}).json()
    return users, game(False), game(True)


def assignment(game, users, positions):
    return {'game_id':game['id'],'field_number':game['field_number'],
            'officials':[{'user_id':users[index]['id'],'position':position} for index,position in enumerate(positions)]}


@pytest.mark.parametrize('positions',[[],['referee'],['down_judge'],['statistician']])
def test_friendly_allows_partial_or_empty_crew(crew,positions):
    users, official, friendly=crew
    row=assignment(friendly,users,positions)
    saved=client.post('/api/games/referee-schedule/confirm',json={'assignments':[row]})
    assert saved.status_code==200
    assigned=client.get(f"/api/games/{friendly['id']}/referees").json()
    assert {r['position'] for r in assigned}==set(positions)
    assert client.post('/api/games/referee-schedule/confirm',json={'assignments':[row]}).status_code==200
    assert client.get(f"/api/games/{friendly['id']}/referees").json()==assigned
    # Omitted slots do not remove assignments previously saved for this friendly.
    assert client.post('/api/games/referee-schedule/confirm',json={'assignments':[assignment(friendly,users,[])]}).status_code==200
    assert client.get(f"/api/games/{friendly['id']}/referees").json()==assigned


@pytest.mark.parametrize('positions',[[],['referee'],['down_judge']])
def test_official_game_cannot_claim_to_be_friendly_to_skip_core_positions(crew,positions):
    users, official, friendly=crew
    row={**assignment(official,users,positions),'is_friendly':True}
    rejected=client.post('/api/games/referee-schedule/confirm',json={'assignments':[row]})
    assert rejected.status_code==409 and rejected.json()['detail']=='Referee y Down Judge son obligatorios'
    assert client.get(f"/api/games/{official['id']}/referees").json()==[]


def test_mixed_batch_accepts_full_official_and_partial_friendly_crews(crew):
    users, official, friendly=crew
    rows=[assignment(official,users,['referee','down_judge']),assignment(friendly,users,['statistician'])]
    assert client.post('/api/games/referee-schedule/confirm',json={'assignments':rows}).status_code==200
    assert len(client.get(f"/api/games/{official['id']}/referees").json())==2
    assert [r['position'] for r in client.get(f"/api/games/{friendly['id']}/referees").json()]==['statistician']


def test_invalid_official_rolls_back_the_entire_mixed_review(crew):
    users, official, friendly=crew
    rows=[{**assignment(friendly,users,['statistician']),'field_number':3},assignment(official,users,['referee'])]
    assert client.post('/api/games/referee-schedule/confirm',json={'assignments':rows}).status_code==409
    current=client.get(f"/api/games/{friendly['id']}/details").json()['game']
    assert current['field_number']==friendly['field_number']
    assert client.get(f"/api/games/{friendly['id']}/referees").json()==[]


def test_duplicate_people_and_positions_remain_rejected_in_friendlies(crew):
    users, official, friendly=crew
    for officials in ([{'user_id':users[0]['id'],'position':position} for position in ['referee','down_judge']],
                      [{'user_id':user['id'],'position':'referee'} for user in users[:2]]):
        row={**assignment(friendly,users,[]),'officials':officials}
        response=client.post('/api/games/referee-schedule/confirm',json={'assignments':[row]})
        assert response.status_code==409 and 'repetir' in response.json()['detail']
