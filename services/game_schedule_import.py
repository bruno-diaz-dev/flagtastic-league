"""Parse league game schedules from the supported spreadsheet formats."""

from csv import DictReader, Sniffer
from datetime import datetime, time
from difflib import SequenceMatcher
from io import BytesIO, StringIO
import re
import unicodedata

from openpyxl import load_workbook


class GameScheduleImportError(Exception):
    """Raised when a schedule file cannot be interpreted safely."""


MAX_SCHEDULE_GAMES = 500
CSV_HEADERS = {
    "week": {"week", "jornada", "semana"},
    "field_number": {"field", "field_number", "campo", "cancha"},
    "start_time": {"time", "start_time", "hora", "horario"},
    "home_team": {"home", "home_team", "local", "equipo_local"},
    "away_team": {"away", "away_team", "visitante", "equipo_visitante"},
}


def parse_game_schedule_file(filename, content, teams):
    """Return reviewable game proposals without modifying league data."""
    lower_name = (filename or "").lower()
    if lower_name.endswith(".xlsx"):
        rows = _read_calendar_workbook(content)
    elif lower_name.endswith(".csv"):
        rows = _read_csv(content)
    else:
        raise GameScheduleImportError("Se requiere un archivo XLSX o CSV")

    proposals = [_match_row(row, teams) for row in rows]
    if not proposals:
        raise GameScheduleImportError("El archivo no contiene partidos reconocibles")
    if len(proposals) > MAX_SCHEDULE_GAMES:
        raise GameScheduleImportError(
            f"El archivo no puede contener mas de {MAX_SCHEDULE_GAMES} partidos"
        )
    return {
        "kind": "games",
        "proposals": proposals,
        "matched": sum(proposal["ready"] for proposal in proposals),
        "unmatched": sum(not proposal["ready"] for proposal in proposals),
    }


def _read_calendar_workbook(content):
    try:
        workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
    except Exception as error:
        raise GameScheduleImportError("No se pudo leer el archivo XLSX") from error

    rows = []
    try:
        for sheet in workbook.worksheets:
            week = None
            field_columns = {}
            hour_column = None
            for row_number, values in enumerate(sheet.iter_rows(values_only=True), start=1):
                cells = list(values)
                texts = [_text(value) for value in cells]
                week_value = next((value for value in texts if _week(value)), None)
                if week_value:
                    week = _week(week_value)
                    field_columns = {}
                    hour_column = None
                    continue

                detected_hour_column = next(
                    (index for index, value in enumerate(texts) if _normalize(value) == "hora"),
                    None,
                )
                if detected_hour_column is not None:
                    hour_column = detected_hour_column
                    field_columns = {}
                    for index, value in enumerate(texts):
                        match = re.fullmatch(r"campo\s*([1-8])", _normalize(value))
                        if match and index + 1 < len(cells):
                            field_columns[index] = int(match.group(1))
                    continue

                if week is None or hour_column is None or not field_columns:
                    continue
                scheduled_time = _time_value(cells[hour_column])
                if scheduled_time is None:
                    continue
                for column, field_number in field_columns.items():
                    home = _text(cells[column])
                    away = _text(cells[column + 1])
                    if not home or not away or "copa aguascalientes" in _normalize(home):
                        continue
                    rows.append({
                        "source_row": f"{sheet.title}!{row_number}",
                        "week": week,
                        "field_number": field_number,
                        "start_time": scheduled_time,
                        "home_team": home,
                        "away_team": away,
                    })
    finally:
        workbook.close()
    return rows


def _read_csv(content):
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise GameScheduleImportError("El CSV debe estar codificado en UTF-8") from error
    try:
        dialect = Sniffer().sniff(text[:4096], delimiters=",;")
    except Exception:
        dialect = "excel"
    reader = DictReader(StringIO(text), dialect=dialect)
    if not reader.fieldnames:
        raise GameScheduleImportError("El CSV no contiene encabezados")
    normalized = {_normalize(header): header for header in reader.fieldnames}
    mapped = {}
    for field, aliases in CSV_HEADERS.items():
        match = next((normalized[alias] for alias in aliases if alias in normalized), None)
        if match is None:
            raise GameScheduleImportError(
                "El CSV requiere jornada, campo, hora, local y visitante"
            )
        mapped[field] = match

    rows = []
    for row_number, row in enumerate(reader, start=2):
        if not any(_text(value) for value in row.values()):
            continue
        try:
            week = int(_text(row[mapped["week"]]))
            field_number = int(re.sub(r"\D", "", _text(row[mapped["field_number"]])))
        except (TypeError, ValueError) as error:
            raise GameScheduleImportError(
                f"Fila {row_number}: jornada o campo invalido"
            ) from error
        scheduled_time = _time_value(row[mapped["start_time"]])
        if week < 1 or field_number not in range(1, 9) or scheduled_time is None:
            raise GameScheduleImportError(f"Fila {row_number}: revisa jornada, campo y hora")
        rows.append({
            "source_row": str(row_number),
            "week": week,
            "field_number": field_number,
            "start_time": scheduled_time,
            "home_team": _text(row[mapped["home_team"]]),
            "away_team": _text(row[mapped["away_team"]]),
        })
    return rows


def _match_row(row, teams):
    home = _match_team(row["home_team"], teams)
    away = _match_team(row["away_team"], teams)
    ready = home is not None and away is not None and home["id"] != away["id"]
    return {
        **row,
        "start_time": row["start_time"].strftime("%H:%M"),
        "home_team_id": home["id"] if home else None,
        "home_match": home["name"] if home else None,
        "away_team_id": away["id"] if away else None,
        "away_match": away["name"] if away else None,
        "ready": ready,
    }


def _match_team(label, teams):
    target = _normalize(label)
    candidates = []
    for team in teams:
        score = max(
            SequenceMatcher(None, target, alias).ratio()
            for alias in _team_aliases(team)
        )
        candidates.append((score, team))
    candidates.sort(key=lambda item: item[0], reverse=True)
    if not candidates or candidates[0][0] < 0.88:
        return None
    if len(candidates) > 1 and candidates[0][0] - candidates[1][0] < 0.025:
        return None
    return candidates[0][1]


def _team_aliases(team):
    name = _normalize(team["name"])
    branch = _normalize(team["branch"])
    category = _normalize(team["category"])
    branch_aliases = {
        "femenil": ("fem", "femenil"),
        "varonil": ("var", "varonil"),
        "mixto": ("mix", "mixto"),
    }.get(branch, (branch,))
    category_aliases = (category, category[1:]) if category.startswith("u") else (category,)
    aliases = {name}
    for category_alias in category_aliases:
        aliases.add(f"{name} {category_alias}")
        for branch_alias in branch_aliases:
            aliases.add(f"{name} {branch_alias} {category_alias}")
    return aliases


def _week(value):
    match = re.search(r"(?:semana|jornada)\s*(\d+)", _normalize(value))
    return int(match.group(1)) if match else None


def _time_value(value):
    if isinstance(value, datetime):
        return value.time().replace(second=0, microsecond=0)
    if isinstance(value, time):
        return value.replace(second=0, microsecond=0)
    text = _text(value)
    for pattern in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(text, pattern).time()
        except ValueError:
            pass
    return None


def _text(value):
    return "" if value is None else str(value).strip()


def _normalize(value):
    text = unicodedata.normalize("NFKD", _text(value).lower())
    text = "".join(character for character in text if not unicodedata.combining(character))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text).split())
