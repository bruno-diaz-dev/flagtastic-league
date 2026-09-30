"""Parse the league's official multi-sheet Excel statistics workbook."""

from collections import Counter, defaultdict
from io import BytesIO
import re
import unicodedata

from openpyxl import load_workbook

from models import ALLOWED_BRANCHES, ALLOWED_CATEGORIES


class StatisticsFileError(Exception):
    """Raised when an uploaded workbook cannot be imported safely."""


HEADER_ALIASES = {
    "rama": "branch", "branch": "branch",
    "categoria": "category", "category": "category",
    "equipo": "team", "team": "team",
    "numero": "jersey_number", "numero_de_jersey": "jersey_number",
    "jersey_number": "jersey_number",
    "puntos": "points", "points": "points",
    "recepciones": "receptions", "receptions": "receptions",
    "intercepciones": "interceptions", "interceptions": "interceptions",
    "capturas": "sacks", "sacks": "sacks",
    "tacleadas": "tackles", "tackles": "tackles",
    "pases_completos": "passes_completed",
    "passes_completed": "passes_completed",
    "pases_lanzados": "passes_attempted",
    "passes_attempted": "passes_attempted"
}
REQUIRED_COLUMNS = {
    "branch", "category", "team", "jersey_number", "points",
    "receptions", "interceptions", "sacks", "tackles",
    "passes_completed", "passes_attempted"
}
WEEK_SHEET_PATTERN = re.compile(r"^wk\s*(\d+)$", re.IGNORECASE)

# Official labels used in the league workbook. Values are jersey numbers;
# repeated occurrences represent repeated events by that player.
EVENT_METRICS = {
    "intentos pase": ("passes_attempted", 1),
    "completos pase": ("receptions", 1),
    "intercepciones def": ("interceptions", 1),
    "sacks": ("sacks", 1),
    "tacleo": ("tackles", 1),
    "6 puntos": ("points", 6),
    "2 puntos": ("points", 2),
    "1 puntos": ("points", 1),
    "td": ("points", 6),
    "conv 1": ("points", 1),
    "conv 2": ("points", 2)
}
IDENTITY_EVENT_LABELS = set(EVENT_METRICS) | {
    "asistencia", "puntos pase", "intercepciones pase", "para % pases"
}


def _normalized_text(value):
    text = unicodedata.normalize("NFKD", str(value or "").strip())
    return "".join(character for character in text if not unicodedata.combining(character)).casefold()


def _normalize_header(value):
    return _normalized_text(value).replace(" ", "_")


def _division_from_official_category(value, sheet_name, row_number):
    """Map compact workbook categories onto the application's division fields."""
    category = _normalized_text(value).replace(" ", "")
    match = re.fullmatch(r"(fem|var|mix)?u?(6|8|10|12|14|16|18|libre)", category)
    if not match:
        raise StatisticsFileError(
            f"{sheet_name}, fila {row_number}: categoria desconocida: {value}"
        )
    prefix, age = match.groups()
    branch = {"fem": "femenil", "var": "varonil", "mix": "mixto"}.get(
        prefix,
        "mixto"
    )
    normalized_category = "libre" if age == "libre" else f"u{age}"
    return branch, normalized_category


def _jersey_numbers(values):
    for value in values:
        if isinstance(value, bool) or value is None:
            continue
        try:
            number = int(value)
        except (TypeError, ValueError):
            continue
        if number >= 0 and number == value:
            yield number


def _official_event_values(values):
    """Return the 50 source cells, excluding the workbook's helper formulas."""
    return values[3:53]


def _score_block(block):
    """Infer a final score from touchdowns and conversion event rows."""
    scoring_values = {"td": 6, "conv 1": 1, "conv 2": 2}
    return sum(
        len(list(_jersey_numbers(_official_event_values(values)))) * value
        for values in block
        if (value := scoring_values.get(_normalized_text(values[2]))) is not None
    )


def _defensive_events(block):
    """Provide a stable tiebreak when the workbook omits part of a score."""
    labels = {"intercepciones def", "sacks", "tacleo"}
    return sum(
        len(list(_jersey_numbers(_official_event_values(values))))
        for values in block
        if _normalized_text(values[2]) in labels
    )


def _parse_official_games(sheet, week):
    """Read consecutive 15-row team blocks as inferred game results."""
    rows = list(sheet.iter_rows(min_row=2, values_only=True))
    blocks = []
    for start in range(0, len(rows), 15):
        block = rows[start:start + 15]
        if len(block) < 15 or not block[0][0]:
            continue
        branch, category = _division_from_official_category(
            block[0][1], sheet.title, start + 2
        )
        blocks.append({
            "branch": branch,
            "category": category,
            "team": str(block[0][0]).strip(),
            "score": _score_block(block),
            "defensive_events": _defensive_events(block)
        })

    if len(blocks) % 2:
        raise StatisticsFileError(
            f"{sheet.title}: existe un equipo sin rival en los bloques de partido"
        )

    games = []
    for index in range(0, len(blocks), 2):
        home, away = blocks[index:index + 2]
        if (home["branch"], home["category"]) != (
            away["branch"], away["category"]
        ):
            raise StatisticsFileError(
                f"{sheet.title}: los rivales no pertenecen a la misma division"
            )
        home_score, away_score = home["score"], away["score"]
        if home_score == away_score:
            # The source tracks individual events, not an official scoreboard.
            # Break inferred ties deterministically because league games cannot tie.
            if away["defensive_events"] > home["defensive_events"]:
                away_score += 1
            else:
                home_score += 1
        games.append({
            "week": week,
            "branch": home["branch"],
            "category": home["category"],
            "home_team": home["team"],
            "away_team": away["team"],
            "home_score": home_score,
            "away_score": away_score
        })
    return games


def _parse_official_week_sheet(sheet, week):
    """Preserve each 15-row team block as statistics for one exact game."""
    players = defaultdict(lambda: Counter({
        "points": 0, "receptions": 0, "interceptions": 0,
        "sacks": 0, "tackles": 0, "passes_completed": 0,
        "passes_attempted": 0
    }))
    source_rows = list(sheet.iter_rows(min_row=2, values_only=True))
    blocks = [
        source_rows[start:start + 15]
        for start in range(0, len(source_rows), 15)
        if len(source_rows[start:start + 15]) == 15
        and source_rows[start:start + 15][0][0]
    ]
    for block_index, block in enumerate(blocks):
        team = str(block[0][0]).strip()
        branch, category = _division_from_official_category(
            block[0][1], sheet.title, block_index * 15 + 2
        )
        game_index = block_index // 2
        for values in block:
            label = _normalized_text(values[2])
            if label not in IDENTITY_EVENT_LABELS:
                continue
            numbers = list(_jersey_numbers(_official_event_values(values)))
            for jersey_number in numbers:
                players[(game_index, branch, category, team, jersey_number)]
            metric = EVENT_METRICS.get(label)
            if metric:
                metric_name, multiplier = metric
                for jersey_number, count in Counter(numbers).items():
                    players[(game_index, branch, category, team, jersey_number)][metric_name] += count * multiplier
            elif label == "para % pases":
                for jersey_number, count in Counter(numbers).items():
                    identity = (game_index, branch, category, team, jersey_number)
                    players[identity]["passes_completed"] += count
                    players[identity]["passes_attempted"] += count

    rows = []
    for (game_index, branch, category, team, jersey_number), metrics in players.items():
        rows.append({
            "branch": branch,
            "category": category,
            "team": team,
            "jersey_number": jersey_number,
            "game_index": game_index,
            **dict(metrics)
        })
    rows.sort(key=lambda row: (
        row["branch"], row["category"], row["team"].casefold(),
        row["jersey_number"]
    ))
    if not rows:
        raise StatisticsFileError(
            f"La hoja de jornada {week} no contiene estadisticas reconocibles"
        )
    return rows


def _non_negative_integer(value, row_number, label):
    if isinstance(value, bool):
        raise StatisticsFileError(f"Fila {row_number}: {label} debe ser entero")
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise StatisticsFileError(f"Fila {row_number}: {label} debe ser entero")
    if number < 0 or number != value:
        raise StatisticsFileError(
            f"Fila {row_number}: {label} debe ser un entero no negativo"
        )
    return number


def _parse_flat_sheet(sheet):
    """Keep support for the application's compact one-row-per-player template."""
    raw_headers = next(sheet.iter_rows(min_row=1, max_row=1, values_only=True), ())
    headers = [HEADER_ALIASES.get(_normalize_header(value)) for value in raw_headers]
    if None in headers or len(headers) != len(REQUIRED_COLUMNS) or set(headers) != REQUIRED_COLUMNS:
        raise StatisticsFileError(
            "El archivo no tiene hojas Wk ni las columnas de la plantilla compacta"
        )
    rows = []
    for row_number, values in enumerate(sheet.iter_rows(min_row=2, values_only=True), 2):
        if all(value is None or str(value).strip() == "" for value in values):
            continue
        data = dict(zip(headers, values))
        branch = str(data["branch"] or "").strip().lower()
        category = str(data["category"] or "").strip().lower()
        team = str(data["team"] or "").strip()
        if branch not in ALLOWED_BRANCHES or category not in ALLOWED_CATEGORIES or not team:
            raise StatisticsFileError(f"Fila {row_number}: division o equipo invalido")
        completed = _non_negative_integer(data["passes_completed"], row_number, "pases_completos")
        attempted = _non_negative_integer(data["passes_attempted"], row_number, "pases_lanzados")
        if completed > attempted:
            raise StatisticsFileError(f"Fila {row_number}: los pases completos exceden los lanzados")
        rows.append({
            "branch": branch, "category": category, "team": team,
            "jersey_number": _non_negative_integer(data["jersey_number"], row_number, "numero"),
            "points": _non_negative_integer(data["points"], row_number, "puntos"),
            "receptions": _non_negative_integer(data["receptions"], row_number, "recepciones"),
            "interceptions": _non_negative_integer(data["interceptions"], row_number, "intercepciones"),
            "sacks": _non_negative_integer(data["sacks"], row_number, "capturas"),
            "tackles": _non_negative_integer(data["tackles"], row_number, "tacleadas"),
            "passes_completed": completed, "passes_attempted": attempted
        })
    return rows


def parse_statistics_workbook(content, selected_week=None):
    """Return `{week: rows}` from the official workbook or compact template."""
    try:
        workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
    except Exception as error:
        raise StatisticsFileError("El archivo no es un Excel valido") from error
    try:
        week_sheets = []
        for sheet in workbook.worksheets:
            match = WEEK_SHEET_PATTERN.fullmatch(sheet.title.strip())
            if match:
                week_sheets.append((int(match.group(1)), sheet))
        if week_sheets:
            parsed = {
                week: _parse_official_week_sheet(sheet, week)
                for week, sheet in week_sheets
                if selected_week is None or week == selected_week
            }
            if not parsed:
                raise StatisticsFileError(
                    f"El archivo no contiene la jornada {selected_week}"
                )
            return parsed
        if selected_week is None:
            raise StatisticsFileError(
                "La plantilla compacta requiere seleccionar una jornada"
            )
        rows = _parse_flat_sheet(workbook.active)
        if not rows:
            raise StatisticsFileError("El archivo no contiene estadisticas")
        return {selected_week: rows}
    finally:
        workbook.close()


def parse_games_workbook(content, selected_week=None):
    """Return inferred games from the paired team blocks in official sheets."""
    try:
        workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
    except Exception as error:
        raise StatisticsFileError("El archivo no es un Excel valido") from error
    try:
        parsed = {}
        for sheet in workbook.worksheets:
            match = WEEK_SHEET_PATTERN.fullmatch(sheet.title.strip())
            if not match:
                continue
            week = int(match.group(1))
            if selected_week is None or week == selected_week:
                parsed[week] = _parse_official_games(sheet, week)
        if not parsed:
            raise StatisticsFileError("El archivo no contiene partidos por jornada")
        return parsed
    finally:
        workbook.close()
