"""Workbook layout regressions independent of database state."""
from io import BytesIO

import pytest
from openpyxl import Workbook

from services.statistics_import import (
    StatisticsFileError, parse_games_workbook, parse_statistics_workbook,
)


def workbook_bytes(repeated_header=False, empty_week=False, invalid=False):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = 'Wk 1'
    header = ['Equipo', 'Categoria', 'Estadistica']
    sheet.append(header)
    labels = ['Intentos Pase', 'Completos Pase', 'Para % pases', 'Puntos Pase',
              '6 Puntos', '2 Puntos', '1 Puntos', 'Intercepciones Pase', 'TD',
              'Conv 1', 'Conv 2', 'Sacks', 'Tacleo', 'Intercepciones Def', 'Asistencia']
    for index, team in enumerate(('Home', 'Away')):
        if index and repeated_header:
            sheet.append(header)
        for label in labels:
            sheet.append([team, 'unknown' if invalid else 'U8', label,
                          7 if label in ('TD', 'Asistencia') else None])
    if empty_week:
        empty = workbook.create_sheet('Wk 2')
        empty.append(header)
        for label in labels:
            empty.append([None, None, label])
    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


def test_repeated_headers_and_unused_week_templates_preserve_import():
    baseline = workbook_bytes()
    repeated = workbook_bytes(repeated_header=True, empty_week=True)
    assert parse_statistics_workbook(repeated) == parse_statistics_workbook(baseline)
    assert parse_games_workbook(repeated) == parse_games_workbook(baseline)
    assert set(parse_statistics_workbook(repeated)) == {1}


def test_invalid_populated_week_is_not_silently_skipped():
    with pytest.raises(StatisticsFileError, match='categoria desconocida'):
        parse_statistics_workbook(workbook_bytes(invalid=True, empty_week=True))


def test_selected_empty_week_still_reports_an_error():
    with pytest.raises(StatisticsFileError, match='jornada 2'):
        parse_statistics_workbook(workbook_bytes(empty_week=True), selected_week=2)


@pytest.mark.parametrize('label,expected', [
    ('U14 Varonil', ('varonil', 'u14')),
    ('U14 Femenil', ('femenil', 'u14')),
    ('Libre Mixto', ('mixto', 'libre')),
    ('Var Libre', ('varonil', 'libre')),
    ('FemU12', ('femenil', 'u12')),
])
def test_official_category_accepts_full_names_and_suffixes(label, expected):
    from services.statistics_import import _division_from_official_category
    assert _division_from_official_category(label, 'Wk 1', 182) == expected


def test_passing_points_are_not_personal_scoring_but_rushing_td_is():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = 'Wk 1'
    labels = ['Intentos Pase', 'Completos Pase', 'Para % pases', 'Puntos Pase',
              '6 Puntos', '2 Puntos', '1 Puntos', 'Intercepciones Pase', 'TD',
              'Conv 1', 'Conv 2', 'Sacks', 'Tacleo', 'Intercepciones Def', 'Asistencia']
    values = {'6 Puntos': [5] * 7, '2 Puntos': [5] * 7, 'TD': [17, 5], 'Conv 2': [17], 'Asistencia': [5, 17]}
    sheet.append(['Equipo', 'Categoria', 'Estadistica'])
    for label in labels:
        sheet.append(['Diablos', 'Libre Femenil', label, *values.get(label, [])])
    for label in labels:
        sheet.append(['Rivals', 'Libre Femenil', label])
    output = BytesIO()
    workbook.save(output)
    workbook.close()
    rows = parse_statistics_workbook(output.getvalue())[1]
    by_number = {row['jersey_number']: row for row in rows}
    assert by_number[5]['points'] == 6  # Only her actual rushing touchdown.
    assert by_number[17]['points'] == 8


@pytest.mark.parametrize('attempts,completions', [(26, 14), (14, 14), (26, 0), (0, 0)])
def test_official_attempts_already_include_completed_passes(attempts, completions):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = 'Wk 1'
    labels = ['Intentos Pase', 'Completos Pase', 'Para % pases', 'Puntos Pase',
              '6 Puntos', '2 Puntos', '1 Puntos', 'Intercepciones Pase', 'TD',
              'Conv 1', 'Conv 2', 'Sacks', 'Tacleo', 'Intercepciones Def', 'Asistencia']
    sheet.append(['Equipo', 'Categoria', 'Estadistica'])
    for label in labels:
        values = [8] * attempts if label == 'Intentos Pase' else [8] * completions if label == 'Para % pases' else [8] if label == 'Asistencia' else []
        sheet.append(['Storms', 'Mix Libre', label, *values])
    output = BytesIO()
    workbook.save(output)
    workbook.close()
    row = parse_statistics_workbook(output.getvalue())[1][0]
    assert row['passes_attempted'] == attempts
    assert row['passes_completed'] == completions


def test_official_completions_exceeding_attempts_are_rejected():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = 'Wk 1'
    labels = ['Intentos Pase', 'Completos Pase', 'Para % pases', 'Puntos Pase',
              '6 Puntos', '2 Puntos', '1 Puntos', 'Intercepciones Pase', 'TD',
              'Conv 1', 'Conv 2', 'Sacks', 'Tacleo', 'Intercepciones Def', 'Asistencia']
    sheet.append(['Equipo', 'Categoria', 'Estadistica'])
    for label in labels:
        sheet.append(['Example', 'Mix Libre', label, *([8] if label == 'Para % pases' else [])])
    output = BytesIO()
    workbook.save(output)
    workbook.close()
    with pytest.raises(StatisticsFileError, match='completos exceden'):
        parse_statistics_workbook(output.getvalue())


@pytest.mark.parametrize('jersey', [0, 8])
def test_incomplete_official_passing_warns_and_preserves_other_metrics(jersey):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = 'Wk 2'
    labels = ['Intentos Pase', 'Completos Pase', 'Para % pases', 'Puntos Pase',
              '6 Puntos', '2 Puntos', '1 Puntos', 'Intercepciones Pase', 'TD',
              'Conv 1', 'Conv 2', 'Sacks', 'Tacleo', 'Intercepciones Def', 'Asistencia']
    sheet.append(['Equipo', 'Categoria', 'Estadistica'])
    events = {'Completos Pase': [20], 'Para % pases': [jersey],
              'TD': [20], 'Tacleo': [jersey]}
    for label in labels:
        sheet.append(['Example', 'Fem 14', label, *events.get(label, [])])
    output = BytesIO()
    workbook.save(output)
    workbook.close()
    warnings = []
    rows = parse_statistics_workbook(output.getvalue(), warnings=warnings)[2]
    by_number = {row['jersey_number']: row for row in rows}
    assert by_number[20]['receptions'] == 1
    assert by_number[20]['points'] == 6
    assert by_number[jersey]['tackles'] == 1
    assert by_number[jersey]['passes_completed'] == 0
    assert by_number[jersey]['passes_attempted'] == 0
    assert by_number[jersey]['passing_incomplete'] is True
    assert len(warnings) == 1
    assert warnings[0]['source_completed'] == 1
    assert warnings[0]['source_attempted'] == 0
    assert warnings[0]['jersey_number'] == jersey
    assert warnings[0]['sheet'] == 'Wk 2'
    assert warnings[0]['row'] == 2


@pytest.mark.parametrize('names,source_category,expected_category,confirmed', [
    (('Diablos Rojo','Lanceros'),'Mix U18','u18',True),
    (('Diablos Amarillo','UCA'),'Mix U18','u18',True),
    (('Diablos','Ravens'),'Var Libre','libre',True),
    (('Other Home','Other Away'),'Mix U18','u18',False),
])
@pytest.mark.parametrize('week,expected_branch',[(3,'femenil'),(4,None)])
def test_only_confirmed_jornada_three_pairs_change_branch(names,source_category,expected_category,confirmed,week,expected_branch):
    workbook=Workbook();sheet=workbook.active;sheet.title=f'Wk {week}'
    sheet.append(['Equipo','Categoria','Estadistica'])
    labels=['Intentos Pase','Completos Pase','Para % pases','Puntos Pase',
            '6 Puntos','2 Puntos','1 Puntos','Intercepciones Pase','TD',
            'Conv 1','Conv 2','Sacks','Tacleo','Intercepciones Def','Asistencia']
    for team in names:
        for label in labels:sheet.append([team,source_category,label,7 if label=='TD' else None])
    content=BytesIO();workbook.save(content);workbook.close()
    rows=parse_statistics_workbook(content.getvalue())[week]
    games=parse_games_workbook(content.getvalue())[week]
    branch=(expected_branch if confirmed else None) or ('varonil' if source_category=='Var Libre' else 'mixto')
    assert {row['branch'] for row in rows}=={branch}
    assert {game['branch'] for game in games}=={branch}
    assert {row['category'] for row in rows}=={expected_category}
    assert {game['category'] for game in games}=={expected_category}
    assert sum(row['points'] for row in rows)==12
    assert {row['game_index'] for row in rows}=={0}


@pytest.mark.parametrize('event,jersey', [('TD', 7), ('Asistencia', 0)])
@pytest.mark.parametrize('populated_indices', [(0, 2), (1,)])
def test_empty_game_pairs_are_omitted_without_shifting_later_player_indices(event, jersey, populated_indices):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = 'Wk 3'
    sheet.append(['Equipo', 'Categoria', 'Estadistica'])
    labels = ['Intentos Pase', 'Completos Pase', 'Para % pases', 'Puntos Pase',
              '6 Puntos', '2 Puntos', '1 Puntos', 'Intercepciones Pase', 'TD',
              'Conv 1', 'Conv 2', 'Sacks', 'Tacleo', 'Intercepciones Def', 'Asistencia']
    for game_index in range(3):
        for side in ('Home', 'Away'):
            for label in labels:
                values = [jersey] if game_index in populated_indices and side == 'Home' and label == event else []
                # Helper totals must not make a blank scheduled game count as played.
                sheet.append([side, 'Fem U14', label, *values])
                sheet.cell(sheet.max_row, 54, 999)
    content = BytesIO()
    workbook.save(content)
    workbook.close()

    rows = parse_statistics_workbook(content.getvalue())[3]
    games = parse_games_workbook(content.getvalue())[3]
    assert [game['game_index'] for game in games] == list(populated_indices)
    assert {row['game_index'] for row in rows} == set(populated_indices)
    assert {row['jersey_number'] for row in rows} == {jersey}
    assert all(game['home_team'] == 'Home' and game['away_team'] == 'Away' for game in games)


def quarterback_workbook():
    """Real-file shape: "Puntos Pase" holds point values aligned with the QB
    jersey in "6/2/1 Puntos"; "Intercepciones Pase" holds the thrower."""
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = 'Wk 1'
    labels = ['Intentos Pase', 'Completos Pase', 'Para % pases', 'Puntos Pase',
              '6 Puntos', '2 Puntos', '1 Puntos', 'Intercepciones Pase', 'TD',
              'Conv 1', 'Conv 2', 'Sacks', 'Tacleo', 'Intercepciones Def', 'Asistencia']
    values = {
        'Intentos Pase': [30, 30, 30, 30, 24], 'Completos Pase': [7, 7, 9],
        'Para % pases': [30, 30, 24], 'Puntos Pase': [6, 2, 6],
        # #30 threw a TD and a 2-point conversion; #24 threw a TD.
        '6 Puntos': [30, 24], '2 Puntos': [30], '1 Puntos': [11],
        # #30 threw one interception; #77 never passed in this game.
        'Intercepciones Pase': [30, 77], 'TD': [7, 9], 'Conv 2': [7],
        'Asistencia': [30, 24, 7, 9],
    }
    sheet.append(['Equipo', 'Categoria', 'Estadistica'])
    for label in labels:
        sheet.append(['Vikingos', 'U8', label, *values.get(label, [])])
    for label in labels:
        sheet.append(['Rivals', 'U8', label])
    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


def test_quarterback_points_and_interceptions_credit_only_the_thrower():
    warnings = []
    rows = parse_statistics_workbook(quarterback_workbook(), warnings=warnings)[1]
    by_number = {row['jersey_number']: row for row in rows}
    assert (by_number[30]['passing_points'], by_number[30]['passes_intercepted']) == (8, 1)
    assert (by_number[24]['passing_points'], by_number[24]['passes_intercepted']) == (6, 0)
    # Passing points are not personal scoring; receivers keep their own points.
    assert by_number[30]['points'] == 0
    assert by_number[7]['points'] == 8
    # "Puntos Pase" values (6, 2) are not jerseys, and non-throwers are never
    # credited or given empty rows.
    assert {2, 6, 11, 77}.isdisjoint(by_number)
    assert sorted((w['reason'], w['jersey_number']) for w in warnings) == [
        ('interception_thrower_unresolved', 77),
        ('passing_points_thrower_unresolved', 11),
    ]


BLOCK_LABELS = ['Intentos Pase', 'Completos Pase', 'Para % pases', 'Puntos Pase',
                '6 Puntos', '2 Puntos', '1 Puntos', 'Intercepciones Pase', 'TD',
                'Conv 1', 'Conv 2', 'Sacks', 'Tacleo', 'Intercepciones Def', 'Asistencia']


def sheets_workbook(sheets):
    """sheets: {title: [(team, category, {label: jerseys})]} in block order."""
    workbook = Workbook()
    workbook.remove(workbook.active)
    for title, blocks in sheets.items():
        sheet = workbook.create_sheet(title)
        sheet.append(['Equipo', 'Categoria', 'Estadistica'])
        for team, category, values in blocks:
            for label in BLOCK_LABELS:
                sheet.append([team, category, label, *values.get(label, [])])
    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


def test_import_mode_skips_only_the_game_with_an_unknown_category():
    content = sheets_workbook({'Wk 1': [
        ('Lobos', 'Var Libre', {'TD': [7]}), ('Pitbulls', 'Var Libre', {'TD': [9]}),
        ('Halcones', 'Categoria rara', {'TD': [5]}), ('Ravens', 'Var Libre', {'TD': [3]}),
    ]})
    warnings = []
    rows = parse_statistics_workbook(content, warnings=warnings)[1]
    assert {row['team'] for row in rows} == {'Lobos', 'Pitbulls'}
    assert [w['reason'] for w in warnings] == ['unknown_category']
    games = parse_games_workbook(content)[1]
    assert [(g['home_team'], g['away_team']) for g in games] == [('Lobos', 'Pitbulls')]
    # Strict callers (scripts) still reject the workbook.
    with pytest.raises(StatisticsFileError, match='categoria desconocida'):
        parse_statistics_workbook(content)


def test_import_mode_skips_unpaired_and_empty_sheets_but_keeps_valid_ones():
    content = sheets_workbook({
        'Wk 1': [('Lobos', 'Var Libre', {'TD': [7]}), ('Pitbulls', 'Var Libre', {'TD': [9]})],
        # Three blocks: pairs cannot be trusted, so the whole sheet is skipped.
        'Wk 2': [('Lobos', 'Var Libre', {'TD': [7]}), ('Pitbulls', 'Var Libre', {}),
                 ('Ravens', 'Var Libre', {'TD': [3]})],
        # Matchups only, no events yet.
        'Wk 3': [('Lobos', 'Var Libre', {}), ('Ravens', 'Var Libre', {})],
    })
    warnings = []
    parsed = parse_statistics_workbook(content, warnings=warnings)
    assert sorted(parsed) == [1]
    assert sorted((w['week'], w['reason']) for w in warnings) == [
        (2, 'unpaired_block'), (3, 'empty_week'),
    ]
    # Skipped and empty sheets yield no games either.
    assert sorted(parse_games_workbook(content)) == [1]


def test_import_mode_skips_games_between_different_divisions():
    content = sheets_workbook({'Wk 1': [
        ('Lobos', 'Var Libre', {'TD': [7]}), ('Pitbulls', 'Var U14', {'TD': [9]}),
        ('Halcones', 'Var Libre', {'TD': [5]}), ('Ravens', 'Var Libre', {'TD': [3]}),
    ]})
    warnings = []
    rows = parse_statistics_workbook(content, warnings=warnings)[1]
    assert {row['team'] for row in rows} == {'Halcones', 'Ravens'}
    assert [w['reason'] for w in warnings] == ['division_mismatch']
    assert [g['game_index'] for g in parse_games_workbook(content)[1]] == [1]
