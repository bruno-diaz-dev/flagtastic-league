"""Parse league game schedules from the supported spreadsheet formats."""

from csv import DictReader, Sniffer
from datetime import datetime, time
from difflib import SequenceMatcher
from io import BytesIO, StringIO
import re
import unicodedata

from openpyxl import load_workbook
from PIL import Image, ImageEnhance, ImageOps, UnidentifiedImageError
import pytesseract

from services.referee_schedule_ocr import _configure_windows_tesseract


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


def parse_game_schedule_image(content, teams):
    """Read the league's visual game grid into reviewable game proposals."""
    _configure_windows_tesseract()
    try:
        image = Image.open(BytesIO(content))
        image.verify()
        image = Image.open(BytesIO(content)).convert("L")
    except (UnidentifiedImageError, OSError) as error:
        raise GameScheduleImportError("La imagen no es valida") from error

    image = ImageOps.autocontrast(image.resize((image.width * 2, image.height * 2)))
    image = ImageEnhance.Contrast(image).enhance(1.5)
    try:
        raw_text = pytesseract.image_to_string(image, config="--psm 6")
        data = pytesseract.image_to_data(
            image, config="--psm 6", output_type=pytesseract.Output.DICT
        )
    except pytesseract.TesseractNotFoundError as error:
        raise GameScheduleImportError(
            "El servidor no tiene instalado el lector OCR"
        ) from error

    week = _week(raw_text)
    field_numbers = {
        int(number) for number in re.findall(r"campo\s*([1-8])", _normalize(raw_text))
    }
    if week is None or not field_numbers:
        raise GameScheduleImportError(
            "No se reconocieron la jornada y los encabezados de campo"
        )
    field_count = max(field_numbers)
    time_rows = []
    for index, value in enumerate(data["text"]):
        parsed_time = _time_value(value)
        if parsed_time is None:
            continue
        center_y = data["top"][index] + data["height"][index] / 2
        if not any(abs(center_y - existing[0]) < image.height * 0.015 for existing in time_rows):
            time_rows.append((center_y, parsed_time))
    time_rows.sort(key=lambda item: item[0])
    if not time_rows:
        raise GameScheduleImportError("No se reconocieron horarios en la imagen")

    time_column_width = image.width * 0.027
    field_width = (image.width - time_column_width) / field_count
    proposals = []
    for row_index, (center_y, scheduled_time) in enumerate(time_rows):
        previous_y = time_rows[row_index - 1][0] if row_index else center_y - image.height * 0.04
        next_y = time_rows[row_index + 1][0] if row_index + 1 < len(time_rows) else center_y + image.height * 0.04
        top = max(0, round((previous_y + center_y) / 2))
        bottom = min(image.height, round((center_y + next_y) / 2))
        for field_index in range(field_count):
            left = time_column_width + field_index * field_width
            middle = left + field_width / 2
            right = left + field_width
            home_text = _ocr_team_cell(image, left, middle, top, bottom)
            away_text = _ocr_team_cell(image, middle, right, top, bottom)
            if not home_text or not away_text:
                continue
            proposals.append(_match_row({
                "source_row": f"Imagen, fila {row_index + 1}",
                "week": week,
                "field_number": field_index + 1,
                "start_time": scheduled_time,
                "home_team": home_text,
                "away_team": away_text,
            }, teams))

    if not proposals:
        raise GameScheduleImportError("No se reconocieron partidos en la imagen")
    return {
        "kind": "games",
        "proposals": proposals,
        "matched": sum(proposal["ready"] for proposal in proposals),
        "unmatched": sum(not proposal["ready"] for proposal in proposals),
        "raw_text": raw_text.strip(),
    }


def parse_game_schedule_ocr_words(image_width, image_height, words, teams):
    """Build schedule proposals from browser-side OCR words and coordinates."""
    normalized_words = [
        {
            "text": _text(word["text"]),
            "left": int(word["left"]),
            "top": int(word["top"]),
            "width": int(word["width"]),
            "height": int(word["height"]),
        }
        for word in words
        if _text(word.get("text"))
    ]
    raw_text = " ".join(word["text"] for word in normalized_words)
    week = _week(raw_text)
    field_numbers = {
        int(number)
        for number in re.findall(r"campo\s*([1-8])", _normalize(raw_text))
    }
    if week is None or not field_numbers:
        raise GameScheduleImportError(
            "No se reconocieron la jornada y los encabezados de campo"
        )

    field_count = max(field_numbers)
    time_rows = []
    for word in normalized_words:
        parsed_time = _time_value(word["text"])
        if parsed_time is None:
            continue
        center_y = word["top"] + word["height"] / 2
        if not any(
            abs(center_y - existing[0]) < image_height * 0.015
            for existing in time_rows
        ):
            time_rows.append((center_y, parsed_time))
    time_rows.sort(key=lambda item: item[0])
    if not time_rows:
        raise GameScheduleImportError("No se reconocieron horarios en la imagen")

    time_column_width = image_width * 0.027
    field_width = (image_width - time_column_width) / field_count
    proposals = []
    for row_index, (center_y, scheduled_time) in enumerate(time_rows):
        previous_y = (
            time_rows[row_index - 1][0]
            if row_index
            else center_y - image_height * 0.04
        )
        next_y = (
            time_rows[row_index + 1][0]
            if row_index + 1 < len(time_rows)
            else center_y + image_height * 0.04
        )
        top = max(0, (previous_y + center_y) / 2)
        bottom = min(image_height, (center_y + next_y) / 2)

        for field_index in range(field_count):
            left = time_column_width + field_index * field_width
            middle = left + field_width / 2
            right = left + field_width
            home_text = _words_in_cell(
                normalized_words, left, middle, top, bottom
            )
            away_text = _words_in_cell(
                normalized_words, middle, right, top, bottom
            )
            if not home_text or not away_text:
                continue
            proposals.append(_match_row({
                "source_row": f"Imagen, fila {row_index + 1}",
                "week": week,
                "field_number": field_index + 1,
                "start_time": scheduled_time,
                "home_team": home_text,
                "away_team": away_text,
            }, teams))

    if not proposals:
        raise GameScheduleImportError("No se reconocieron partidos en la imagen")
    if len(proposals) > MAX_SCHEDULE_GAMES:
        raise GameScheduleImportError(
            f"La imagen no puede contener mas de {MAX_SCHEDULE_GAMES} partidos"
        )
    return {
        "kind": "games",
        "proposals": proposals,
        "matched": sum(proposal["ready"] for proposal in proposals),
        "unmatched": sum(not proposal["ready"] for proposal in proposals),
        "raw_text": raw_text.strip(),
    }


def _words_in_cell(words, left, right, top, bottom):
    selected = []
    for word in words:
        center_x = word["left"] + word["width"] / 2
        center_y = word["top"] + word["height"] / 2
        if left <= center_x < right and top <= center_y < bottom:
            selected.append(word)
    selected.sort(key=lambda word: (word["top"], word["left"]))
    return " ".join(word["text"] for word in selected).strip()


def _ocr_team_cell(image, left, right, top, bottom):
    crop = ImageOps.autocontrast(image.crop((round(left), top, round(right), bottom)))
    return pytesseract.image_to_string(crop, config="--psm 6").strip().replace("\n", " ")


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
