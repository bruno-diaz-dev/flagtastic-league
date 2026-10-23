from uuid import uuid4

from fastapi.testclient import TestClient

from database import get_connection
from dependencies.auth import require_authenticated_user, require_league_admin
from main import app
from models import UserCreate
from repositories.games import assign_referee
from repositories.referees import update_referee_aka
from repositories.users import create_user


def test_audit_rejects_non_admins_before_loading_account_details(monkeypatch):
    app.dependency_overrides.pop(require_league_admin, None)
    calls = []
    def audit():
        calls.append(True)
        return {"officials": [], "weeks": []}
    monkeypatch.setattr("routes.referees.get_referee_assignment_audit", audit)
    with TestClient(app) as client:
        assert client.get('/api/referees/assignments').status_code == 401
        for role in ['referee', 'player', 'team_representative']:
            app.dependency_overrides[require_authenticated_user] = lambda role=role: {"id": 1, "role": role}
            assert client.get('/api/referees/assignments').status_code == 403
        assert calls == []
        app.dependency_overrides[require_authenticated_user] = lambda: {"id": 1, "role": "league_admin"}
        result = client.get('/api/referees/assignments')
        assert result.status_code == 200
        assert result.headers['cache-control'] == 'private, no-store'
        assert calls == [True]


def test_audit_keeps_zoe_accounts_and_unassigned_officials_separate():
    suffix = uuid4().hex[:12]
    people = [create_user(UserCreate(email=f'{alias}-{suffix}@example.test',
              name=name, password='supersecret', role='referee'))
              for alias,name in [('one','Zoe García'),('two','Zoé Pérez'),('zero','Sin asignaciones')]]
    for person,aka in zip(people, ['Zoe','Zoé','Sin juegos']):
        update_referee_aka(person['id'], aka)
    with TestClient(app) as client:
        teams = [client.post('/api/teams',json={'name':name+suffix,'branch':'mixto','category':'libre'}).json()['id']
                 for name in ['Audit Home','Audit Away']]
        games = [client.post('/api/games',json={'home_team_id':teams[0],'away_team_id':teams[1],
                 'week':week,'field_number':7,'start_time':'23:50'}).json()['id'] for week in [96,97]]
        assign_referee(games[0],people[0]['id'],'referee',people[0]['id'])
        assign_referee(games[1],people[0]['id'],'down_judge',people[0]['id'])
        assign_referee(games[1],people[1]['id'],'statistician',people[0]['id'])
        assigned = client.get(f'/api/games/{games[1]}/referees').json()
        assert {row['id']:row['display_name'] for row in assigned} == {
            people[0]['id']:'Zoe', people[1]['id']:'Zoé',
        }
        # A former/inactive referee with stored assignments must remain auditable.
        with get_connection() as connection:
            connection.execute("UPDATE users SET status='inactive' WHERE id=%s",(people[1]['id'],))
            connection.execute("DELETE FROM user_roles WHERE user_id=%s AND role='referee'",(people[1]['id'],))
        response = client.get('/api/referees/assignments')
        assert response.status_code == 200
        audit = {person['id']:person for person in response.json()['officials']}
        one,two,zero = [audit[person['id']] for person in people]
        assert one['display_name']=='Zoe' and two['display_name']=='Zoé'
        assert one['email']!=two['email']
        assert {(game['id'],game['position']) for game in one['games']} == {(games[0],'referee'),(games[1],'down_judge')}
        assert [(game['id'],game['position']) for game in two['games']] == [(games[1],'statistician')]
        assert zero['games']==[]
        assert two['status']=='inactive'
        assert {game['week'] for game in one['games']}=={96,97}
        assert all(game['start_time']=='23:50:00' and game['field_number']==7 for game in one['games'])
