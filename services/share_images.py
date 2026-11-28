"""Social preview images (1200x630 PNG) for games, teams and players.

WhatsApp, Facebook and X read ``og:image`` from the page HTML and show it as
the link preview. The images use the league palette and fonts. Player
images never include the profile photo: previews are cached by third-party
services and many players are minors.
"""

from functools import lru_cache
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

WIDTH, HEIGHT = 1200, 630
NAVY_DARK = (4, 16, 39)
NAVY = (13, 30, 66)
NAVY_SOFT = (29, 58, 122)
GOLD = (244, 197, 66)
TEXT = (241, 245, 252)
MUTED = (163, 184, 218)
FAINT = (110, 128, 160)

STATIC = Path(__file__).resolve().parent.parent / "static"
DISPLAY_FONT = STATIC / "fonts" / "barlow-condensed-latin-800-normal.woff2"
DISPLAY_FONT_SEMI = STATIC / "fonts" / "barlow-condensed-latin-600-normal.woff2"
BODY_FONT = STATIC / "fonts" / "inter-latin-wght-normal.woff2"
LOGO = STATIC / "assets" / "flagtastic-logo.png"


@lru_cache(maxsize=64)
def _font(path, size):
    """Load a league font; fall back to Pillow's font where WOFF2 is unsupported."""
    try:
        return ImageFont.truetype(str(path), size)
    except OSError:
        return ImageFont.load_default(size)


def display(size):
    return _font(DISPLAY_FONT, size)


def display_semi(size):
    return _font(DISPLAY_FONT_SEMI, size)


def body(size):
    return _font(BODY_FONT, size)


def _canvas():
    image = Image.new("RGB", (WIDTH, HEIGHT), NAVY_DARK)
    glow = Image.new("L", (WIDTH, HEIGHT), 0)
    ImageDraw.Draw(glow).ellipse((420, -560, 1560, 380), fill=170)
    glow = glow.filter(ImageFilter.GaussianBlur(140))
    image.paste(Image.new("RGB", (WIDTH, HEIGHT), NAVY_SOFT), mask=glow)
    draw = ImageDraw.Draw(image)
    # Yard lines, as on the site's page bands.
    for x in range(120, WIDTH, 120):
        draw.line((x, 0, x, HEIGHT), fill=(22, 36, 66), width=1)
    draw.rectangle((0, HEIGHT - 10, WIDTH, HEIGHT), fill=GOLD)
    return image


def _brand(image):
    """League logo and wordmark in the top-left corner."""
    draw = ImageDraw.Draw(image)
    try:
        logo = Image.open(LOGO).convert("RGBA")
        logo.thumbnail((64, 64))
        image.paste(logo, (56, 44), logo)
    except OSError:
        pass
    font = display(38)
    draw.text((132, 54), "FLAG", font=font, fill=TEXT)
    draw.text((132 + draw.textlength("FLAG", font=font), 54), "TASTIC", font=font, fill=GOLD)


def _fit(draw, text, font_factory, size, max_width, minimum=20):
    """Shrink a font until the text fits, then ellipsize as a last resort."""
    while size > minimum and draw.textlength(text, font=font_factory(size)) > max_width:
        size -= 2
    font = font_factory(size)
    if draw.textlength(text, font=font) <= max_width:
        return text, font
    while text and draw.textlength(text + "…", font=font) > max_width:
        text = text[:-1]
    return text.rstrip() + "…", font


def _circle_logo(content, size, fallback_text):
    """A team logo on a white disc, or its initials on navy."""
    disc = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
    logo = None
    if content:
        try:
            logo = Image.open(BytesIO(content)).convert("RGBA")
        except (OSError, ValueError):
            logo = None
    if logo is not None:
        background = Image.new("RGBA", (size, size), (255, 255, 255, 255))
        corners = [logo.getpixel(point)[3] for point in ((0, 0), (logo.width - 1, 0), (0, logo.height - 1), (logo.width - 1, logo.height - 1))]
        if min(corners) == 255:
            # A square picture with no transparency fills the disc.
            logo = ImageOps.fit(logo, (size, size))
        else:
            logo = ImageOps.contain(logo, (int(size * .86), int(size * .86)))
        background.alpha_composite(logo, ((size - logo.width) // 2, (size - logo.height) // 2))
        disc.paste(background, (0, 0), mask)
    else:
        background = Image.new("RGBA", (size, size), NAVY_SOFT + (255,))
        draw = ImageDraw.Draw(background)
        font = display(int(size * .38))
        draw.text((size / 2, size / 2), fallback_text, font=font, fill=TEXT, anchor="mm")
        disc.paste(background, (0, 0), mask)
    return disc


def initials(name):
    parts = [part for part in str(name or "").split() if part[:1].isalnum()]
    return "".join(part[0] for part in parts[:2]).upper() or "?"


def _png(image):
    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def game_image(game, home_logo=None, away_logo=None):
    """Final score, or the matchup and kickoff for a game still to play."""
    image = _canvas()
    _brand(image)
    draw = ImageDraw.Draw(image)
    completed = (
        game.get("status") == "completed"
        and isinstance(game.get("home_score"), int)
        and isinstance(game.get("away_score"), int)
    )
    label = game.get("label") or ""
    draw.text((WIDTH - 56, 64), label.upper(), font=display_semi(30), fill=MUTED, anchor="ra")

    status = "FINAL" if completed else game.get("when", "POR JUGAR").upper()
    pill_font = display(28)
    pill_width = draw.textlength(status, font=pill_font) + 44
    pill_left = (WIDTH - pill_width) / 2
    draw.rounded_rectangle((pill_left, 150, pill_left + pill_width, 196), radius=23,
                           fill=GOLD if completed else NAVY_SOFT)
    draw.text((WIDTH / 2, 173), status, font=pill_font, fill=NAVY_DARK if completed else TEXT, anchor="mm")

    home, away = game["home_team"], game["away_team"]
    for team, logo, center_x in ((home, home_logo, 260), (away, away_logo, WIDTH - 260)):
        disc = _circle_logo(logo, 168, initials(team["name"]))
        image.paste(disc, (center_x - 84, 236), disc)
        name, font = _fit(draw, team["display_name"], display, 46, 360)
        draw.text((center_x, 440), name, font=font, fill=TEXT, anchor="mt")

    if completed:
        home_score, away_score = game["home_score"], game["away_score"]
        score_font = display(150)
        draw.text((WIDTH / 2 - 34, 330), str(home_score), font=score_font,
                  fill=TEXT if home_score >= away_score else MUTED, anchor="rm")
        draw.text((WIDTH / 2, 330), "–", font=display(80), fill=FAINT, anchor="mm")
        draw.text((WIDTH / 2 + 34, 330), str(away_score), font=score_font,
                  fill=TEXT if away_score >= home_score else MUTED, anchor="lm")
    else:
        draw.text((WIDTH / 2, 320), "VS", font=display(96), fill=GOLD, anchor="mm")
    footer = game.get("footer") or ""
    draw.text((WIDTH / 2, 552), footer, font=body(26), fill=MUTED, anchor="mm")
    return _png(image)


def team_image(team, logo=None):
    """Team card: logo, name, division, record and standing."""
    image = _canvas()
    _brand(image)
    draw = ImageDraw.Draw(image)
    disc = _circle_logo(logo, 300, initials(team["name"]))
    image.paste(disc, (80, 170), disc)

    left = 430
    draw.text((left, 172), team["division"].upper(), font=display_semi(32), fill=GOLD)
    name, font = _fit(draw, team["display_name"], display, 96, WIDTH - left - 56, minimum=44)
    draw.text((left, 210), name.upper(), font=font, fill=TEXT)

    stats = team.get("stats") or []
    x = left
    for value, caption in stats:
        draw.text((x, 360), str(value), font=display(78), fill=TEXT)
        draw.text((x, 448), caption.upper(), font=body(20), fill=FAINT)
        x += max(draw.textlength(str(value), font=display(78)), draw.textlength(caption.upper(), font=body(20))) + 56
    draw.text((left, 540), "Roster, calendario y líderes en FlagTastic", font=body(24), fill=MUTED)
    return _png(image)


def player_image(player):
    """Season card: jersey number, name, team and season totals. No photo."""
    image = _canvas()
    _brand(image)
    draw = ImageDraw.Draw(image)
    jersey = player.get("jersey_number")
    number = f"#{jersey}" if jersey is not None else "#"
    draw.text((56, 150), number, font=display(210), fill=GOLD)

    left = 56
    name, font = _fit(draw, player["display_name"], display, 78, WIDTH - 112, minimum=40)
    draw.text((left, 376), name.upper(), font=font, fill=TEXT)
    draw.text((left, 462), player.get("team_line", ""), font=body(26), fill=MUTED)

    stats = player.get("stats") or []
    x = WIDTH - 56
    for value, caption in reversed(stats):
        caption = caption.upper()
        width = max(draw.textlength(str(value), font=display(84)), draw.textlength(caption, font=body(18)))
        draw.text((x, 170), str(value), font=display(84), fill=TEXT, anchor="ra")
        draw.text((x, 266), caption, font=body(18), fill=FAINT, anchor="ra")
        x -= width + 44
    draw.text((left, 540), player.get("footer", ""), font=body(22), fill=FAINT)
    return _png(image)
