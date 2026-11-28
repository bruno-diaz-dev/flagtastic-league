"""Link previews: Open Graph images and page meta for games, teams and players.

Link scrapers (WhatsApp, Facebook, X) read the page HTML without running
JavaScript, so the game, roster and player page routes ask this module for
their title, description and preview image. Every lookup is best effort: a
database problem only means the generic league preview is used.
"""

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Query, Request, Response

from repositories.dashboard import get_player_dashboard
from repositories.games import get_games
from repositories.standings import get_standings
from repositories.teams import get_team_by_id, get_team_logo
from services import share_images
from services.display_names import display_name, division_label
from settings import PUBLIC_BASE_URL

router = APIRouter(tags=["share"])

LEAGUE_TIMEZONE = ZoneInfo("America/Mexico_City")
WEEKDAYS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
MONTHS = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
          "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
IMAGE_HEADERS = {
    "Cache-Control": "public, max-age=300",
    "Vercel-CDN-Cache-Control": "public, max-age=300",
}
UNIFIED_YOUTH = {"u8", "u10", "u12"}


def site_url(request):
    """Absolute site origin for meta tags; scrapers need absolute URLs."""
    if PUBLIC_BASE_URL and "127.0.0.1" not in PUBLIC_BASE_URL and "localhost" not in PUBLIC_BASE_URL:
        return PUBLIC_BASE_URL
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc
    scheme = request.headers.get("x-forwarded-proto") or request.url.scheme
    return f"{scheme}://{host}"


def default_meta(request):
    base = site_url(request)
    return {
        "title": "FlagTastic Football League",
        "description": "Partidos, marcadores en vivo, tabla de posiciones y líderes de la liga FlagTastic.",
        "image": f"{base}/static/assets/icon-512.png",
        "image_width": 512,
        "image_height": 512,
        "url": f"{base}{request.url.path}",
        "card": "summary",
    }


def _as_date(value):
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)) if value else None
    except ValueError:
        return None


def _as_time(value):
    if isinstance(value, time):
        return value.strftime("%H:%M")
    return str(value)[:5] if value else None


def _long_date(day):
    return f"{WEEKDAYS[day.weekday()]} {day.day} de {MONTHS[day.month - 1]}"


def _when(day):
    if day is None:
        return "Por jugar"
    days = (day - datetime.now(LEAGUE_TIMEZONE).date()).days
    if days == 0:
        return "Hoy"
    if days == 1:
        return "Mañana"
    if days > 1:
        return f"En {days} días"
    return "Por jugar"


def _logo(team_id):
    if not team_id:
        return None
    logo = get_team_logo(team_id)
    return logo["logo_data"] if logo else None


def _find_game(game_id):
    return next((game for game in get_games() if game["id"] == game_id), None)


def _game_card(game):
    """Everything the game preview shows, shared by the image and the meta tags."""
    home, away = game["home_team"], game["away_team"]
    home_name, away_name = display_name(home["name"]), display_name(away["name"])
    completed = (
        game["status"] == "completed"
        and isinstance(game.get("home_score"), int)
        and isinstance(game.get("away_score"), int)
    )
    division = division_label(home.get("branch"), home.get("category")) if home.get("category") else ""
    label = game.get("bracket_label") or (f"Jornada {game['week']} · {division}" if division else f"Jornada {game['week']}")
    day = _as_date(game.get("game_date"))
    kickoff = _as_time(game.get("start_time"))
    place = " · ".join(filter(None, [
        _long_date(day) if day else None,
        game.get("venue"),
        kickoff,
        f"Campo {game['field_number']}" if game.get("field_number") else None,
    ]))
    if completed:
        title = f"{home_name} {game['home_score']} – {game['away_score']} {away_name}"
        description = f"Final · {label}. Marcador y estadísticas en FlagTastic."
    else:
        title = f"{home_name} vs {away_name}"
        description = f"{label}. {place or 'Horario por confirmar'}."
    return {
        "title": title,
        "description": description,
        "image": {
            "status": game["status"] if completed else "scheduled",
            "home_score": game.get("home_score"),
            "away_score": game.get("away_score"),
            "label": label,
            "when": "Final" if completed else _when(day),
            "footer": place if not completed else f"Jornada {game['week']} · FlagTastic Football League",
            "home_team": {"name": home["name"], "display_name": home_name},
            "away_team": {"name": away["name"], "display_name": away_name},
        },
        # The image URL changes with the score so previews refresh after the final.
        "version": f"{game['status']}-{game.get('home_score')}-{game.get('away_score')}",
    }


def _team_card(team_id):
    team = get_team_by_id(team_id)
    if team is None:
        return None
    category = str(team.get("category") or "").lower()
    branch = "mixto" if category in UNIFIED_YOUTH else team.get("branch")
    standings = get_standings(branch, category) if category and branch else []
    position = next((index + 1 for index, row in enumerate(standings) if row["team_id"] == team_id), None)
    row = standings[position - 1] if position else None
    name = display_name(team["name"])
    division = division_label(team.get("branch"), team.get("category"))
    stats = []
    if row:
        stats = [
            (f"{row['wins']}-{row['losses']}", "Récord"),
            (f"#{position}", f"de {len(standings)} en la tabla"),
            (f"{row['point_difference']:+d}", "Diferencia"),
        ]
    description = (
        f"{division}. Récord {row['wins']}-{row['losses']}, lugar {position} de {len(standings)}. Roster, calendario y líderes."
        if row else f"{division}. Roster, calendario y líderes del equipo."
    )
    return {
        "title": f"{name} · Roster",
        "description": description,
        "image": {"name": team["name"], "display_name": name, "division": division, "stats": stats},
        "version": f"{row['wins']}-{row['losses']}-{position}" if row else "0",
    }


def _player_card(player_id, team_id=None):
    profile = get_player_dashboard(player_id, team_id=team_id)
    if profile is None:
        return None
    player = profile["player"]
    shown = player.get("aka") or display_name(player["name"])
    team = next((item for item in profile.get("teams", []) if item["team_id"] == profile.get("selected_team_id")), None)
    statistics = (team or {}).get("statistics") or profile.get("statistics") or {}
    team_line = ""
    if team:
        team_line = f"{display_name(team['team_name'])} · {division_label(team.get('branch'), team.get('category'))}"
    stats = [
        (statistics.get("points", 0), "Puntos"),
        (statistics.get("receptions", 0), "Recepciones"),
        (statistics.get("tackles", 0), "Tacleadas"),
        (statistics.get("interceptions", 0), "Intercepciones"),
    ]
    summary = ", ".join(f"{value} {caption.lower()}" for value, caption in stats)
    return {
        "title": f"{shown} · Temporada",
        "description": f"{team_line}. {summary}." if team_line else f"{summary}.",
        "image": {
            "display_name": shown,
            "jersey_number": (team or {}).get("jersey_number"),
            "team_line": team_line,
            "stats": stats,
            "footer": f"{statistics.get('weeks', 0)} jornadas con estadísticas · FlagTastic Football League",
        },
        "team_id": (team or {}).get("team_id"),
        "version": "-".join(str(value) for value, _ in stats),
    }


def _meta(request, card, image_path):
    meta = default_meta(request)
    base = site_url(request)
    meta.update({
        "title": card["title"],
        "description": card["description"],
        "image": f"{base}{image_path}",
        "image_width": share_images.WIDTH,
        "image_height": share_images.HEIGHT,
        "card": "summary_large_image",
    })
    return meta


def game_meta(request, game_id):
    try:
        game = _find_game(game_id)
        if game is None:
            return default_meta(request)
        card = _game_card(game)
        return _meta(request, card, f"/og/games/{game_id}.png?v={card['version']}")
    except Exception:
        return default_meta(request)


def team_meta(request, team_id):
    try:
        card = _team_card(team_id)
        if card is None:
            return default_meta(request)
        return _meta(request, card, f"/og/teams/{team_id}.png?v={card['version']}")
    except Exception:
        return default_meta(request)


def player_meta(request, player_id, team_id=None):
    try:
        card = _player_card(player_id, team_id)
        if card is None:
            return default_meta(request)
        query = f"team_id={card['team_id']}&" if card.get("team_id") else ""
        return _meta(request, card, f"/og/players/{player_id}.png?{query}v={card['version']}")
    except Exception:
        return default_meta(request)


@router.get("/og/games/{game_id}.png")
def game_share_image(game_id: int):
    """Preview image with the final score, or the matchup still to play."""
    game = _find_game(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="Partido no encontrado")
    card = _game_card(game)
    content = share_images.game_image(
        card["image"], _logo(game["home_team"].get("id")), _logo(game["away_team"].get("id"))
    )
    return Response(content=content, media_type="image/png", headers=IMAGE_HEADERS)


@router.get("/og/teams/{team_id}.png")
def team_share_image(team_id: int):
    """Preview image with the team's logo, record and standing."""
    card = _team_card(team_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    content = share_images.team_image(card["image"], _logo(team_id))
    return Response(content=content, media_type="image/png", headers=IMAGE_HEADERS)


@router.get("/og/players/{player_id}.png")
def player_share_image(player_id: int, team_id: int | None = Query(default=None, gt=0)):
    """Preview image with the player's season totals (never the photo)."""
    card = _player_card(player_id, team_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Jugador no encontrado")
    content = share_images.player_image(card["image"])
    return Response(content=content, media_type="image/png", headers=IMAGE_HEADERS)
