"""Extract reviewable referee assignments from an uploaded schedule image."""

from difflib import SequenceMatcher
from io import BytesIO
import os
import re
import shutil
import unicodedata

from PIL import Image, ImageEnhance, ImageOps, UnidentifiedImageError
import pytesseract


POSITION_ALIASES = {
    "referee": ("referee", "ref principal", "arbitro principal"),
    "down_judge": ("down judge", "dj"),
    "field_judge": ("field judge", "fj"),
    "side_judge": ("side judge", "sj"),
    "statistician": ("estadistico", "estadistica", "statistician", "stats")
}
POSITION_ORDER = tuple(POSITION_ALIASES)
GRID_FOUR_POSITION_ORDER = (
    "referee", "down_judge", "field_judge", "statistician"
)
GRID_FIVE_POSITION_ORDER = (
    "referee", "down_judge", "field_judge", "side_judge", "statistician"
)


class RefereeScheduleImageError(Exception):
    """Raised when an uploaded schedule cannot be read safely."""


def _normalized(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    return " ".join(
        "".join(char for char in text if not unicodedata.combining(char))
        .casefold().split()
    )


def _configure_windows_tesseract():
    """Use the standard Windows install path when it is not on PATH yet."""
    if shutil.which("tesseract"):
        return
    candidate = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.path.exists(candidate):
        pytesseract.pytesseract.tesseract_cmd = candidate


def _contains_name(text, name):
    normalized_name = _normalized(name)
    if normalized_name in text:
        return True
    # OCR commonly drops one character from a team or referee name.
    words = text.split()
    width = len(normalized_name.split())
    return any(
        SequenceMatcher(None, normalized_name, " ".join(words[index:index + width])).ratio() >= 0.86
        for index in range(max(0, len(words) - width + 1))
    )


def _detected_position(context, name, fallback_index):
    """Infer a nearby role label, falling back to the printed name order."""
    normalized_name = _normalized(name)
    name_index = context.find(normalized_name)
    nearby = context[max(0, name_index - 35):name_index + len(normalized_name) + 35]
    for position, aliases in POSITION_ALIASES.items():
        if any(alias in nearby for alias in aliases):
            return position
    return POSITION_ORDER[min(fallback_index, len(POSITION_ORDER) - 1)]


def _best_referee(segment, referees):
    """Match one printed AKA/name cell to the closest active account."""
    normalized_segment = _normalized(segment)
    if not normalized_segment:
        return None
    candidates = []
    for referee in referees:
        display_name = referee.get("display_name") or referee["name"]
        normalized_name = _normalized(display_name)
        score = SequenceMatcher(None, normalized_segment, normalized_name).ratio()
        if normalized_name in normalized_segment or normalized_segment in normalized_name:
            score = max(score, 0.95)
        candidates.append((score, referee, display_name))
    if not candidates:
        return None
    score, referee, display_name = max(candidates, key=lambda candidate: candidate[0])
    return (referee, display_name) if score >= 0.72 else None


def _division_hints(text):
    """Read division abbreviations printed beside team names in the grid."""
    normalized = _normalized(text)
    branch = next((
        value for token, value in (
            ("fem", "femenil"), ("var", "varonil"), ("mix", "mixto")
        ) if re.search(rf"\b{token}\w*\b", normalized)
    ), None)
    category_match = re.search(r"\bu?\s*(6|8|10|12|14|16|18)\b", normalized)
    category = f"u{category_match.group(1)}" if category_match else None
    if "libre" in normalized:
        category = "libre"
    return branch, category


def _game_match_score(text, game):
    """Score both team names and any readable division hints."""
    normalized = _normalized(text)
    home_name = _normalized(game["home_team"]["name"])
    away_name = _normalized(game["away_team"]["name"])
    home_score = 1.0 if home_name in normalized else SequenceMatcher(
        None, home_name, normalized
    ).ratio()
    away_score = 1.0 if away_name in normalized else SequenceMatcher(
        None, away_name, normalized
    ).ratio()
    branch, category = _division_hints(text)
    if branch and game["home_team"]["branch"] != branch:
        return 0
    if category and game["home_team"]["category"] != category:
        return 0
    return home_score + away_score


def _parse_grid_schedule(image, raw_text, games, referees):
    """Parse the league's week-by-field role sheet using word coordinates."""
    normalized_text = _normalized(raw_text)
    week_match = re.search(r"semana\s*(\d+)", normalized_text)
    if not week_match or image.width / image.height < 1.7:
        return []

    data = pytesseract.image_to_data(
        image, config="--psm 6", output_type=pytesseract.Output.DICT
    )
    words = []
    for index, text in enumerate(data["text"]):
        if not text.strip():
            continue
        words.append({
            "text": text.strip(),
            "x": data["left"][index] + data["width"][index] / 2,
            "y": data["top"][index] + data["height"][index] / 2
        })

    week = int(week_match.group(1))
    field_count = len(re.findall(r"campo\s*[1-8]", normalized_text)) or 6
    field_count = min(8, max(1, field_count))
    time_column_width = image.width * 0.027
    field_width = (image.width - time_column_width) / field_count
    week_games = [game for game in games if game["week"] == week]
    proposals = []
    used_games = set()

    # The time column spans both the teams and officials subrows. Its solid
    # horizontal borders therefore reveal the real hour boundaries even when
    # an empty hour is shorter than the others.
    time_width = max(1, round(time_column_width))
    border_candidates = []
    for y in range(round(image.height * 0.06), image.height):
        dark_pixels = sum(
            pixel < 100
            for pixel in image.crop((0, y, time_width, y + 1)).getdata()
        )
        if dark_pixels >= time_width * 0.7:
            border_candidates.append(y)
    borders = []
    for y in border_candidates:
        if not borders or y - borders[-1] > 2:
            borders.append(y)
    if len(borders) < 2:
        return []

    for row_index, (row_top, row_bottom) in enumerate(zip(borders, borders[1:])):
        official_split = row_top + (row_bottom - row_top) * 0.62
        for field_index in range(field_count):
            left = time_column_width + field_index * field_width
            right = left + field_width
            cell_words = [
                word for word in words
                if left <= word["x"] < right
                and row_top <= word["y"] < row_bottom
            ]
            official_text = " ".join(
                word["text"] for word in cell_words if word["y"] >= official_split
            )
            if "/" not in official_text:
                continue

            # Colored team cells are more reliable when OCR runs on the cell
            # alone instead of across the full multicolor schedule.
            team_crop = image.crop((
                round(left), row_top + 1, round(right), round(official_split)
            ))
            team_crop = ImageOps.autocontrast(team_crop)
            team_text = pytesseract.image_to_string(
                team_crop, config="--psm 6"
            ).strip().replace("\n", " ")
            if not team_text:
                continue

            candidates = [game for game in week_games if game["id"] not in used_games]
            if not candidates:
                continue
            scored = sorted(
                ((_game_match_score(team_text, game), game) for game in candidates),
                key=lambda candidate: candidate[0], reverse=True
            )
            if not scored or scored[0][0] < 1.45:
                continue
            game = scored[0][1]

            # Empty slash-separated slots are meaningful in this sheet.
            segments = [segment.strip() for segment in official_text.split("/")]
            position_order = (
                GRID_FIVE_POSITION_ORDER
                if len(segments) >= 5
                else GRID_FOUR_POSITION_ORDER
            )
            officials = []
            for position, segment in zip(position_order, segments):
                matched = _best_referee(segment, referees)
                if matched is None:
                    continue
                referee, display_name = matched
                officials.append({
                    "user_id": referee["id"],
                    "name": display_name,
                    "position": position
                })
            proposals.append({
                "game_id": game["id"],
                "game_label": (
                    f"J{game['week']}: {game['home_team']['name']} vs "
                    f"{game['away_team']['name']}"
                ),
                "field_number": field_index + 1,
                "officials": officials,
                "source_text": f"{team_text} | {official_text}",
                "scheduled_time": f"{12 + row_index}:00"
            })
            used_games.add(game["id"])
    return proposals


def parse_referee_schedule_image(content, games, referees):
    """Return assignment proposals without changing official league data."""
    _configure_windows_tesseract()
    try:
        image = Image.open(BytesIO(content))
        image.verify()
        image = Image.open(BytesIO(content)).convert("L")
    except (UnidentifiedImageError, OSError) as error:
        raise RefereeScheduleImageError("La imagen no es valida") from error

    # Upscaling and contrast improve screenshots and compressed messaging images.
    image = ImageOps.autocontrast(image.resize((image.width * 2, image.height * 2)))
    image = ImageEnhance.Contrast(image).enhance(1.5)
    try:
        raw_text = pytesseract.image_to_string(image, config="--psm 6")
    except pytesseract.TesseractNotFoundError as error:
        raise RefereeScheduleImageError(
            "El servidor no tiene instalado el lector OCR"
        ) from error

    grid_proposals = _parse_grid_schedule(image, raw_text, games, referees)
    if grid_proposals:
        return {"proposals": grid_proposals, "raw_text": raw_text.strip()}

    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    proposals = []
    used_games = set()
    for index, line in enumerate(lines):
        # Include adjacent OCR lines because narrow screenshots may wrap a row.
        context = _normalized(" ".join(lines[max(0, index - 1):index + 2]))
        field_match = re.search(r"(?:campo|cancha)\s*#?\s*([1-8])\b", context)
        if not field_match:
            continue
        matched_game = next((
            game for game in games
            if game["id"] not in used_games
            and _contains_name(context, game["home_team"]["name"])
            and _contains_name(context, game["away_team"]["name"])
        ), None)
        if matched_game is None:
            continue
        matched_referees = [
            referee for referee in referees
            if _contains_name(
                context, referee.get("display_name") or referee["name"]
            )
        ]
        officials = []
        used_positions = set()
        for referee in matched_referees:
            position = _detected_position(
                context,
                referee.get("display_name") or referee["name"],
                len(officials)
            )
            if position in used_positions:
                position = next(
                    (candidate for candidate in POSITION_ORDER if candidate not in used_positions),
                    position
                )
            used_positions.add(position)
            officials.append({
                "user_id": referee["id"],
                "name": referee.get("display_name") or referee["name"],
                "position": position
            })
        proposals.append({
            "game_id": matched_game["id"],
            "game_label": (
                f"J{matched_game['week']}: "
                f"{matched_game['home_team']['name']} vs "
                f"{matched_game['away_team']['name']}"
            ),
            "field_number": int(field_match.group(1)),
            "officials": officials,
            "source_text": line
        })
        used_games.add(matched_game["id"])

    if not raw_text.strip():
        raise RefereeScheduleImageError("No se pudo leer texto en la imagen")
    return {"proposals": proposals, "raw_text": raw_text.strip()}
