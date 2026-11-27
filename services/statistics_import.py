"""Parse the league's official multi-sheet Excel statistics workbook."""

from collections import Counter, defaultdict
from io import BytesIO
import re
import unicodedata

from openpyxl import load_workbook

from models import ALLOWED_BRANCHES, ALLOWED_CATEGORIES
from services.divisions import teams_share_game_division


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
    "passes_attempted": "passes_attempted",
    "puntos_pase": "passing_points", "passing_points": "passing_points",
    "intercepciones_lanzadas": "passes_intercepted",
    "passes_intercepted": "passes_intercepted",
}
REQUIRED_COLUMNS = {
    "branch", "category", "team", "jersey_number", "points",
    "receptions", "interceptions", "sacks", "tackles",
    "passes_completed", "passes_attempted"
}
# Older compact templates lack these; their values stay unchanged on update.
OPTIONAL_COLUMNS = {"passing_points", "passes_intercepted"}
WEEK_SHEET_PATTERN = re.compile(r"^wk\s*(\d+)$", re.IGNORECASE)

# Official labels used in the league workbook. Values are jersey numbers;
# repeated occurrences represent repeated events by that player.
EVENT_METRICS = {
    "intentos pase": ("passes_attempted", 1),
    "completos pase": ("receptions", 1),
    "intercepciones def": ("interceptions", 1),
    "sacks": ("sacks", 1),
    "tacleo": ("tackles", 1),
    "td": ("points", 6),
    "conv 1": ("points", 1),
    "conv 2": ("points", 2)
}
IDENTITY_EVENT_LABELS = set(EVENT_METRICS) | {
    "asistencia", "puntos pase", "intercepciones pase", "para % pases",
    "6 puntos", "2 puntos", "1 puntos"
}
# Quarterback rows. "6/2/1 Puntos" carry the jersey of the QB who threw a
# scoring pass (TD, 2-point or 1-point conversion); "Intercepciones Pase"
# carries the jersey of the QB who threw an interception. Both are credited
# only when the jersey passed in that same game block; otherwise the datum is
# reported instead of being attributed to someone else.
PASSING_SCORE_LABELS = {"6 puntos": 6, "2 puntos": 2, "1 puntos": 1}
QUARTERBACK_EVENT_LABELS = {*PASSING_SCORE_LABELS, "intercepciones pase"}
QUARTERBACK_IDENTITY_LABELS = {"intentos pase", "para % pases"}
# "Puntos Pase" holds point values (6, 2, 1) aligned with the rows above, not
# jersey numbers, so it never identifies a player.
NON_JERSEY_LABELS = {"puntos pase"}


def _normalized_text(value):
    text = unicodedata.normalize("NFKD", str(value or "").strip())
    return "".join(character for character in text if not unicodedata.combining(character)).casefold()


def _normalize_header(value):
    return _normalized_text(value).replace(" ", "_")


def _division_from_official_category(value, sheet_name, row_number):
    """Map compact workbook categories onto the application's division fields."""
    category = _normalized_text(value).replace(" ", "")
    for full, short in (("femenil", "fem"), ("femenino", "fem"), ("varonil", "var"), ("masculino", "var"), ("mixto", "mix")):
        category = category.replace(full, short)
    match = re.fullmatch(r"(fem|var|mix)?u?(6|8|10|12|14|16|18|libre)", category)
    if match:
        prefix, age = match.groups()
    else:
        # Regional sheets also write the branch after the age: "U14 Fem".
        suffix = re.fullmatch(
            r"u?(6|8|10|12|14|16|18|libre)(fem|var|mix)",
            category
        )
        if not suffix:
            raise StatisticsFileError(
                f"{sheet_name}, fila {row_number}: categoria desconocida: {value}"
            )
        age, prefix = suffix.groups()
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


def _official_team_blocks(sheet, issues=None):
    """Ignore repeated print headers without shifting fixed-size team blocks.

    With ``issues`` (a list) an incomplete trailing block is reported there
    and skipped; without it the workbook is rejected (strict mode).
    """
    rows = [
        (number, values)
        for number, values in enumerate(
            sheet.iter_rows(min_row=2, max_col=53, values_only=True), 2
        )
        if tuple(_normalized_text(value) for value in values[:3])
        != ("equipo", "categoria", "estadistica")
    ]
    blocks = []
    for start in range(0, len(rows), 15):
        section = rows[start:start + 15]
        if not section or not section[0][1][0]:
            continue
        if len(section) != 15:
            message = f"{sheet.title}, fila {section[0][0]}: bloque de equipo incompleto"
            if issues is None:
                raise StatisticsFileError(message)
            issues.append({
                "reason": "incomplete_block", "row": section[0][0],
                "team_name": str(section[0][1][0]).strip(), "detail": message,
            })
            continue
        blocks.append((section[0][0], [values for _, values in section]))
    return blocks


# Confirmed by the league administrator for the original jornada-3 workbook.
# The age stays unchanged; only these exact paired source labels change branch.
_CONFIRMED_SOURCE_BRANCHES = {
    (3, "mixto", "u18", frozenset({"diablos rojo", "lanceros"})): "femenil",
    (3, "mixto", "u18", frozenset({"diablos amarillo", "uca"})): "femenil",
    (3, "varonil", "libre", frozenset({"diablos", "ravens"})): "femenil",
    # These official sheets label the following completed girls' divisions as
    # Mixto. Exact pair and week are corroborated by the registered schedule.
    (4, "mixto", "u14", frozenset({"black mamba", "vikingos blanco"})): "femenil",
    (4, "mixto", "u14", frozenset({"flamingos", "nomadas amarillo"})): "femenil",
    (4, "mixto", "u14", frozenset({"nomadas amarillo", "pitbulls"})): "femenil",
    (4, "mixto", "u14", frozenset({"nomadas negro", "vikingos blanco"})): "femenil",
    (4, "mixto", "u18", frozenset({"black mamba", "pitbulls"})): "femenil",
    (5, "mixto", "u14", frozenset({"eca", "flamingos"})): "femenil",
    (5, "mixto", "u14", frozenset({"diablos del sol", "ducks"})): "femenil",
}


def _block_has_player_data(block):
    return any(
        next(_jersey_numbers(_official_event_values(values)), None) is not None
        for values in block
        if _normalized_text(values[2]) in IDENTITY_EVENT_LABELS
        and _normalized_text(values[2]) not in NON_JERSEY_LABELS
    )


def _official_blocks_with_divisions(sheet, week, issues=None):
    """Share approved source corrections between player and game readers.

    Strict mode (``issues`` is None) rejects the workbook on a block it cannot
    read. Otherwise the block keeps ``None`` as division, the problem is
    appended to ``issues`` and callers skip that block's game.
    """
    blocks = []
    for row_number, block in _official_team_blocks(sheet, issues):
        try:
            branch, category = _division_from_official_category(
                block[0][1], sheet.title, row_number
            )
        except StatisticsFileError as error:
            if issues is None:
                raise
            issues.append({
                "reason": "unknown_category", "row": row_number,
                "team_name": str(block[0][0]).strip(), "detail": str(error),
            })
            branch = category = None
        blocks.append([row_number, block, branch, category])
    for index in range(0, len(blocks) - 1, 2):
        home, away = blocks[index:index + 2]
        if home[2] is None or home[2:] != away[2:]:
            continue
        names = frozenset(" ".join(_normalized_text(item[1][0][0]).split()) for item in (home, away))
        branch = _CONFIRMED_SOURCE_BRANCHES.get((week, home[2], home[3], names))
        if branch:
            home[2] = away[2] = branch
    return blocks


def _official_sheet_layout(sheet, week, issues):
    """Blocks plus the game pairs that cannot be imported safely.

    Returns ``(blocks, skipped_pairs)``; ``skipped_pairs`` holds the game
    indexes to skip. Both readers use it, so player rows and games are always
    skipped together. Problems are appended to ``issues``.
    """
    blocks = _official_blocks_with_divisions(sheet, week, issues)
    skipped_pairs = set()
    if len(blocks) % 2:
        # The trailing block has no rival. Earlier pairs are kept; any shift
        # is caught later because pairs must match a registered game.
        issues.append({
            "reason": "unpaired_block", "row": blocks[-1][0],
            "team_name": str(blocks[-1][1][0][0]).strip(),
            "detail": (
                f"{sheet.title}, fila {blocks[-1][0]}: el equipo no tiene rival "
                "en los bloques de partido; se omitió ese bloque"
            ),
        })
        skipped_pairs.add((len(blocks) - 1) // 2)
    for index in range(0, len(blocks) - len(blocks) % 2, 2):
        home, away = blocks[index:index + 2]
        if home[2] is None or away[2] is None:
            skipped_pairs.add(index // 2)
            continue
        # Named schedule placeholders carry no data and are skipped anyway.
        if not _block_has_player_data(home[1]) and not _block_has_player_data(away[1]):
            continue
        if not teams_share_game_division(
            {"branch": home[2], "category": home[3]},
            {"branch": away[2], "category": away[3]},
        ):
            issues.append({
                "reason": "division_mismatch", "row": home[0],
                "team_name": f"{str(home[1][0][0]).strip()} vs {str(away[1][0][0]).strip()}",
                "detail": (
                    f"{sheet.title}, fila {home[0]}: los rivales no pertenecen a "
                    "la misma división; se omitió ese partido"
                ),
            })
            skipped_pairs.add(index // 2)
    return blocks, skipped_pairs


def _parse_official_games(sheet, week):
    """Read consecutive 15-row team blocks as inferred game results.

    Games that cannot be read safely are skipped; the statistics reader
    reports the same problems as warnings.
    """
    raw_blocks, skipped_pairs = _official_sheet_layout(sheet, week, [])
    blocks = []
    for row_number, block, branch, category in raw_blocks:
        blocks.append({
            "branch": branch,
            "category": category,
            "team": str(block[0][0]).strip(),
            "has_player_data": _block_has_player_data(block),
            "score": _score_block(block),
            "defensive_events": _defensive_events(block)
        })

    games = []
    for index in range(0, len(blocks), 2):
        if index // 2 in skipped_pairs:
            continue
        home, away = blocks[index:index + 2]
        # Named schedule placeholders are not played results. Keep the source
        # index for later pairs so their player rows still link to the right game.
        if not home["has_player_data"] and not away["has_player_data"]:
            continue
        home_score, away_score = home["score"], away["score"]
        if home_score == away_score:
            # The source tracks individual events, not an official scoreboard.
            # Break inferred ties deterministically because league games cannot tie.
            if away["defensive_events"] > home["defensive_events"]:
                away_score += 1
            else:
                home_score += 1
        games.append({
            "game_index": index // 2,
            "week": week,
            "branch": home["branch"],
            "category": home["category"],
            "home_team": home["team"],
            "away_team": away["team"],
            "home_score": home_score,
            "away_score": away_score
        })
    return games


def _parse_official_week_sheet(sheet, week, warnings=None):
    """Preserve each 15-row team block as statistics for one exact game."""
    players = defaultdict(lambda: Counter({
        "points": 0, "receptions": 0, "interceptions": 0,
        "sacks": 0, "tackles": 0, "passes_completed": 0,
        "passes_attempted": 0, "passing_points": 0, "passes_intercepted": 0
    }))
    if warnings is None:
        # Strict mode (scripts and direct callers): unreadable blocks raise.
        blocks = _official_blocks_with_divisions(sheet, week)
        skipped_pairs = set()
    else:
        # Imports skip the affected game and keep going.
        issues = []
        blocks, skipped_pairs = _official_sheet_layout(sheet, week, issues)
        warnings.extend(
            {**issue, "week": week, "sheet": sheet.title} for issue in issues
        )
    if not blocks:
        return []
    source_rows = {}
    attendance_by_player = set()
    for block_index, (row_number, block, branch, category) in enumerate(blocks):
        team = str(block[0][0]).strip()
        game_index = block_index // 2
        if game_index in skipped_pairs:
            continue
        source_rows[(game_index, branch, category, team)] = row_number
        quarterbacks = {
            jersey_number
            for values in block
            if _normalized_text(values[2]) in QUARTERBACK_IDENTITY_LABELS
            for jersey_number in _jersey_numbers(_official_event_values(values))
        }
        for values in block:
            label = _normalized_text(values[2])
            if label not in IDENTITY_EVENT_LABELS or label in NON_JERSEY_LABELS:
                continue
            numbers = list(_jersey_numbers(_official_event_values(values)))
            if label in QUARTERBACK_EVENT_LABELS:
                for jersey_number, count in Counter(numbers).items():
                    if jersey_number not in quarterbacks:
                        if warnings is not None:
                            warnings.append({
                                "reason": (
                                    "interception_thrower_unresolved"
                                    if label == "intercepciones pase"
                                    else "passing_points_thrower_unresolved"
                                ),
                                "week": week, "sheet": sheet.title,
                                "row": row_number, "team_name": team,
                                "branch": branch, "category": category,
                                "jersey_number": jersey_number,
                                "game_index": game_index, "count": count,
                                "label": str(values[2]).strip(),
                            })
                        continue
                    identity = (game_index, branch, category, team, jersey_number)
                    if label == "intercepciones pase":
                        players[identity]["passes_intercepted"] += count
                    else:
                        players[identity]["passing_points"] += (
                            count * PASSING_SCORE_LABELS[label]
                        )
                continue
            if label == "asistencia":
                attendance_by_player.update(
                    (game_index, branch, category, team, jersey_number)
                    for jersey_number in numbers
                )
            for jersey_number in numbers:
                players[(game_index, branch, category, team, jersey_number)]
            metric = EVENT_METRICS.get(label)
            if metric:
                metric_name, multiplier = metric
                for jersey_number, count in Counter(numbers).items():
                    players[(game_index, branch, category, team, jersey_number)][metric_name] += count * multiplier
            elif label == "para % pases":
                # The workbook counts attempts separately (including completed
                # passes). These QB markers supply completions only.
                for jersey_number, count in Counter(numbers).items():
                    identity = (game_index, branch, category, team, jersey_number)
                    players[identity]["passes_completed"] += count

    rows = []
    for (game_index, branch, category, team, jersey_number), metrics in players.items():
        passing_incomplete = metrics["passes_completed"] > metrics["passes_attempted"]
        if passing_incomplete:
            if warnings is None:
                raise StatisticsFileError(
                    f"{sheet.title}, equipo {team}, jersey {jersey_number}: "
                    "los pases completos exceden los intentos registrados"
                )
            warnings.append({
                "reason": "incomplete_passing", "week": week,
                "sheet": sheet.title,
                "row": source_rows[(game_index, branch, category, team)],
                "team_name": team, "branch": branch, "category": category,
                "jersey_number": jersey_number, "game_index": game_index,
                "source_completed": metrics["passes_completed"],
                "source_attempted": metrics["passes_attempted"],
            })
            # Do not infer attempts, guess a QB, or publish an invented rating.
            # The repository keeps the existing passing pair on an update.
            metrics["passes_completed"] = metrics["passes_attempted"] = 0
        rows.append({
            "branch": branch,
            "category": category,
            "team": team,
            "jersey_number": jersey_number,
            "game_index": game_index,
            **dict(metrics),
            "attendance": (game_index, branch, category, team, jersey_number) in attendance_by_player,
            **({"passing_incomplete": True} if passing_incomplete else {})
        })
    rows.sort(key=lambda row: (
        row["branch"], row["category"], row["team"].casefold(),
        row["jersey_number"]
    ))
    if not rows:
        message = f"La hoja de jornada {week} no contiene estadisticas reconocibles"
        if warnings is None:
            raise StatisticsFileError(message)
        # A future sheet that only lists matchups has nothing to import yet.
        warnings.append({
            "reason": "empty_week", "week": week, "sheet": sheet.title,
            "row": None, "team_name": "",
            "detail": message + "; se omitió esa hoja",
        })
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
    if (None in headers or len(headers) != len(set(headers))
            or not REQUIRED_COLUMNS <= set(headers)
            or not set(headers) <= REQUIRED_COLUMNS | OPTIONAL_COLUMNS):
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
            "passes_completed": completed, "passes_attempted": attempted,
            **{
                column: (
                    # Missing column or blank cell: keep the stored value.
                    None if data.get(column) is None
                    or str(data[column]).strip() == ""
                    else _non_negative_integer(data[column], row_number, column)
                )
                for column in sorted(OPTIONAL_COLUMNS)
            },
        })
    return rows


def parse_statistics_workbook(content, selected_week=None, *, warnings=None):
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
                week: _parse_official_week_sheet(sheet, week, warnings)
                for week, sheet in week_sheets
                if selected_week is None or week == selected_week
            }
            parsed = {week: rows for week, rows in parsed.items() if rows}
            if not parsed:
                raise StatisticsFileError(
                    f"El archivo no contiene la jornada {selected_week}"
                    if selected_week is not None
                    else "El archivo no contiene estadisticas importables"
                )
            return parsed
        if selected_week is None:
            raise StatisticsFileError(
                "La plantilla compacta requiere seleccionar una jornada"
            )
        # Real league spreadsheets sometimes have a single "Hoja1" sheet
        # containing official 15-row team blocks instead of a named Wk sheet.
        # Require the admin-selected week: never guess one from a filename.
        if len(workbook.worksheets) == 1:
            active = workbook.active
            headers = next(
                active.iter_rows(min_row=1, max_row=1, max_col=3, values_only=True),
                ()
            )
            if tuple(_normalized_text(v) for v in headers) == (
                "equipo", "categoria", "estadistica"
            ):
                return {selected_week: _parse_official_week_sheet(active, selected_week, warnings)}
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
                games = _parse_official_games(sheet, week)
                if games:
                    parsed[week] = games
        if not parsed and selected_week is not None and len(workbook.worksheets) == 1:
            active = workbook.active
            headers = next(
                active.iter_rows(min_row=1, max_row=1, max_col=3, values_only=True),
                ()
            )
            if tuple(_normalized_text(v) for v in headers) == (
                "equipo", "categoria", "estadistica"
            ):
                parsed[selected_week] = _parse_official_games(active, selected_week)
        if not parsed:
            raise StatisticsFileError("El archivo no contiene partidos por jornada")
        return parsed
    finally:
        workbook.close()

