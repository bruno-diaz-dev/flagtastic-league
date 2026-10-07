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
