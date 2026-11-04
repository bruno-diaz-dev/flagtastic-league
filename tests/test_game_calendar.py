"""Calendar context must distinguish days/venues without duplicating or moving other games."""
from datetime import date
from io import BytesIO
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook

from database import get_connection
from main import app
from models import UserCreate
from repositories.games import assign_referee, get_games_for_referee
from repositories.users import create_user
from services.game_schedule_import import parse_game_schedule_file
from services.referee_schedule_import import parse_referee_schedule_file

client = TestClient(app)

@pytest.fixture(autouse=True)
def empty_calendar():
    with get_connection() as connection:
        connection.execute('DELETE FROM teams')


def teams():
    return [client.post('/api/teams', json={'name': name, 'branch': 'mixto', 'category': 'libre'}).json()['id'] for name in ['Calendar A', 'Calendar B']]


def fixture(ids, **changes):
    return {'home_team_id': ids[0], 'away_team_id': ids[1], 'week': 5, 'field_number': 1, 'start_time': '20:15', **changes}


def referee():
    return create_user(UserCreate(email=f'calendar-{uuid4().hex}@example.test', name='Calendar official', password='supersecret', role='referee'))['id']


def test_distinct_dates_and_venues_allow_same_field_time_and_identical_reimport_is_idempotent():
    ids = teams()
    rows = [fixture(ids, game_date='2026-11-04', venue='Cuernos Largos'),
            fixture(ids, game_date='2026-11-08', venue='Cuernos Largos'),
            fixture(ids, game_date='2026-11-08', venue='Cd Industrial')]
    first = client.post('/api/games/schedule/confirm', json={'games': rows})
    assert first.status_code == 200 and first.json() == {'created': 3, 'updated': 0, 'skipped': 0}
    capabilities = client.get('/api/games/calendar-capabilities')
    assert capabilities.json() == {'date_and_venue': True} and capabilities.headers['cache-control'] == 'no-store'
    before = client.get('/api/games').json()
    assert {(g['game_date'], g['venue']) for g in before} == {(r['game_date'], r['venue']) for r in rows}
    second = client.post('/api/games/schedule/confirm', json={'games': rows})
    assert second.status_code == 200 and second.json()['skipped'] == 3
    assert [g['id'] for g in client.get('/api/games').json()] == [g['id'] for g in before]
    # An old file that omits context cannot silently choose one of these games.
    ambiguous = client.post('/api/games/schedule/confirm', json={'games': [fixture(ids)]})
    assert ambiguous.status_code == 409
    assert len(client.get('/api/games').json()) == 3


def test_slot_conflicts_use_date_venue_and_normalized_venue_names():
    ids = teams()
    assert client.post('/api/games', json=fixture(ids, game_date='2026-11-04', venue='  Cuernos   Largos ')).status_code == 201
    assert client.post('/api/games', json=fixture(ids, game_date='2026-11-04', venue='cuernos largos')).status_code == 409
    assert client.post('/api/games', json=fixture(ids, game_date='2026-11-05', venue='Cuernos Largos')).status_code == 201
    assert client.post('/api/games', json=fixture(ids, game_date='2026-11-04', venue='Cd Industrial')).status_code == 201


def test_context_can_enrich_one_legacy_game_preserving_id_and_crew():
    ids = teams()
    created = client.post('/api/games', json=fixture(ids)).json()
    official = referee()
    assign_referee(created['id'], official, 'referee', official)
    row = fixture(ids, game_date='2026-11-04', venue='Cuernos Largos')
    response = client.post('/api/games/schedule/confirm', json={'games': [row]})
    assert response.status_code == 200 and response.json()['updated'] == 1
    game = client.get('/api/games').json()[0]
    assert game['id'] == created['id'] and game['game_date'] == '2026-11-04'
    assert client.get(f"/api/games/{created['id']}/referees").json()[0]['id'] == official
    assert get_games_for_referee(official)[0]['game_date'] == date(2026, 11, 4)
    assert client.post('/api/games/schedule/confirm', json={'games': [fixture(ids)]}).json()['skipped'] == 1
    assert client.get('/api/games').json()[0]['venue'] == 'Cuernos Largos'


def test_edit_calendar_preserves_id_and_crew_checks_destination_and_allows_clearing():
    ids = teams()
    game = client.post('/api/games', json=fixture(ids, game_date='2026-11-04', venue='Cuernos Largos')).json()
    other = client.post('/api/games', json=fixture(ids, game_date='2026-11-08', venue='Cd Industrial')).json()
    official = referee()
    assign_referee(game['id'], official, 'down_judge', official)
    path = f"/api/games/{game['id']}/schedule"
    assert client.patch(path, json={'start_time': '20:15', 'game_date': '2026-11-08', 'venue': 'Cd Industrial'}).status_code == 409
    moved = client.patch(path, json={'start_time': '21:15', 'game_date': '2026-11-08', 'venue': 'Cd Industrial'})
    assert moved.status_code == 200 and moved.json()['id'] == game['id']
    assert moved.json()['game_date'] == '2026-11-08'
    retained = client.patch(path, json={'start_time': '22:15'})
    assert retained.status_code == 200 and retained.json()['venue'] == 'Cd Industrial'
    assert client.get(f"/api/games/{game['id']}/referees").json()[0]['id'] == official
    cleared = client.patch(path, json={'start_time': '22:15', 'game_date': None, 'venue': None})
    assert cleared.status_code == 200 and cleared.json()['game_date'] is None and cleared.json()['venue'] is None
    assert next(g for g in client.get('/api/games').json() if g['id'] == other['id'])['start_time'] == '20:15:00'


def test_xlsx_blocks_keep_independent_dates_and_invalid_date_requires_review():
    workbook = Workbook(); sheet = workbook.active
    sheet.append(['Semana 5'])
    sheet.append(['Sede:', 'Cuernos Largos', None, 'Fecha:', date(2026, 11, 4)])
    sheet.append(['Hora', 'Campo 1', None])
    sheet.append(['20:15', 'Calendar A', 'Calendar B'])
    sheet.append(['Sede:', 'Cd Industrial', None, 'Fecha:', '#REF!'])
    sheet.append(['Hora', 'Campo 1', None])
    sheet.append(['20:15', 'Calendar A', 'Calendar B'])
    content = BytesIO(); workbook.save(content)
    catalog = [{'id': n+1, 'name': name, 'branch': 'mixto', 'category': 'libre'} for n, name in enumerate(['Calendar A', 'Calendar B'])]
    result = parse_game_schedule_file('rol.xlsx', content.getvalue(), catalog, selected_week=5)
    first, second = result['proposals']
    assert first['game_date'] == '2026-11-04' and first['venue'] == 'Cuernos Largos' and first['ready']
    assert 'game_date' not in second and second['date_required'] and second['venue'] == 'Cd Industrial' and not second['ready']
    assert len(result['warnings']) == 1


def test_csv_reads_local_calendar_dates_and_venues():
    source = ('jornada,campo,hora,local,visitante,fecha,sede\n'
              '5,1,20:15,Calendar A,Calendar B,04/11/2026,Cuernos Largos\n').encode()
    result = parse_game_schedule_file('rol.csv', source, [], selected_week=5)
    assert result['proposals'][0]['game_date'] == '2026-11-04'
    assert result['proposals'][0]['venue'] == 'Cuernos Largos'


def test_official_matching_distinguishes_same_opponents_on_different_days_and_venues():
    ids = teams()
    records = [client.post('/api/games', json=fixture(ids, game_date=day, venue=venue)).json()
               for day, venue in [('2026-11-04', 'Cuernos Largos'), ('2026-11-08', 'Cuernos Largos'), ('2026-11-08', 'Cd Industrial')]]
    source = ('jornada,campo,hora,local,visitante,fecha,sede,referee,down judge\n'
              '5,1,20:15,Calendar A,Calendar B,08/11/2026,Cd Industrial,Ref Uno,Ref Dos\n').encode()
    people = [{'id': 1, 'name': 'Ref Uno'}, {'id': 2, 'name': 'Ref Dos'}]
    result = parse_referee_schedule_file('arbitros.csv', source, client.get('/api/games').json(), people, selected_week=5)
    assert result['warnings'] == [] and result['proposals'][0]['game_id'] == records[2]['id']
    assert result['proposals'][0]['game_date'] == '2026-11-08'
    invalid = parse_referee_schedule_file('arbitros.csv', source.replace(b'08/11/2026', b'#REF!'), client.get('/api/games').json(), people, selected_week=5)
    assert invalid['proposals'][0]['game_date'] == '2026-11-08' and 'date_required' not in invalid['proposals'][0]
    assert 'se conserva' in invalid['warnings'][0]


def test_older_schema_remains_readable_and_rejects_metadata_writes_without_losing_data():
    ids = teams()
    game = client.post('/api/games', json=fixture(ids)).json()
    with get_connection() as connection:
        connection.execute('ALTER TABLE games DROP COLUMN game_date, DROP COLUMN venue')
    try:
        assert client.get('/api/games/calendar-capabilities').json() == {'date_and_venue': False}
        response = client.get('/api/games')
        assert response.status_code == 200 and response.json()[0]['game_date'] is None
        new = client.post('/api/games', json=fixture(ids, start_time='21:15', game_date='2026-11-04', venue='Cuernos Largos'))
        assert new.status_code == 409 and 'Supabase' in new.json()['detail']
        assert client.patch(f"/api/games/{game['id']}/schedule", json={'start_time': '21:15'}).status_code == 200
        assert client.patch(f"/api/games/{game['id']}/schedule", json={'start_time': '22:15', 'game_date': '2026-11-04'}).status_code == 409
        assert len(client.get('/api/games').json()) == 1
    finally:
        from importlib import import_module
        schema = import_module('migrations.versions.0b8d2f4a6c90_game_dates_and_venues').SCHEMA
        with get_connection() as connection:
            connection.execute(schema)


def test_crew_import_preserves_calendar_when_missing_and_validates_cross_day_moves():
    from models import RefereeScheduleAssignment, GameOfficialAssignment
    from repositories.games import apply_referee_schedule, ScheduleConflictError
    ids = teams()
    game = client.post('/api/games', json=fixture(ids, game_date='2026-11-04', venue='Cuernos Largos')).json()
    other = client.post('/api/games', json=fixture(ids, game_date='2026-11-08', venue='Cd Industrial')).json()
    official = referee()
    assignment = lambda **changes: RefereeScheduleAssignment(game_id=game['id'], field_number=1,
        officials=[GameOfficialAssignment(user_id=official, position='referee')], **changes)
    apply_referee_schedule([assignment(scheduled_time='20:15')], official)
    assert client.get('/api/games').json()[0]['game_date'] == '2026-11-04'
    with pytest.raises(ScheduleConflictError):
        apply_referee_schedule([assignment(scheduled_time='20:15', game_date='2026-11-08', venue='Cd Industrial')], official)
    apply_referee_schedule([assignment(scheduled_time='21:15', game_date='2026-11-08', venue='Cd Industrial')], official)
    moved = next(g for g in client.get('/api/games').json() if g['id'] == game['id'])
    assert moved['game_date'] == '2026-11-08' and moved['venue'] == 'Cd Industrial'
    assert client.get(f"/api/games/{game['id']}/referees").json()[0]['id'] == official


def test_calendar_import_rolls_back_if_a_later_row_would_rewrite_a_completed_game():
    ids = teams()
    game = client.post('/api/games', json=fixture(ids, game_date='2026-11-08', venue='Cd Industrial')).json()
    assert client.patch(f"/api/games/{game['id']}/score", json={'home_score': 6, 'away_score': 0}).status_code == 200
    third = client.post('/api/teams', json={'name': 'Calendar C', 'branch': 'mixto', 'category': 'libre'}).json()['id']
    result = client.post('/api/games/schedule/confirm', json={'games': [
        fixture(ids, game_date='2026-11-04', venue='Cuernos Largos'),
        fixture([ids[0], third], game_date='2026-11-08', venue='Cd Industrial'),
    ]})
    assert result.status_code == 409
    all_games = client.get('/api/games').json()
    assert len(all_games) == 1 and all_games[0]['id'] == game['id'] and all_games[0]['away_team']['id'] == ids[1]
