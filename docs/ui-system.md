# FlagTastic interface conventions

Styles load in this order on every page: `static/tokens.css`, `static/style.css`, `static/ui.css`, then any page stylesheet.

- `tokens.css` is the single source for colour, type and shape. Use its variables (`--color-*`, `--font-body`, `--font-display`, `--ui-radius*`, `--ui-gap`, `--ui-shadow`) instead of hard-coded values, and add a token there rather than a one-off colour in a page file.
- `ui.css` is the shared visual layer. `style.css` keeps the older functional layout rules.

## Typography

- Fonts are self-hosted in `static/fonts/` under the SIL Open Font License (licence files alongside). No page loads fonts from a third party.
- **Inter** (`--font-body`) is for reading text, forms and tables.
- **Barlow Condensed** (`--font-display`) is for page titles, scores, jersey numbers and statistic totals. Page titles are uppercase. Numbers use tabular figures so columns stay aligned.

## Names

`static/display.js` (loaded by `base.html` before page scripts) only changes how names are shown. Stored names never change.

- `displayName(name)` gives team, player and staff names consistent casing: "DIABLOS DEL SOL" and "diablos del sol" both read "Diablos del Sol". It keeps age categories (U14), initialisms (A.C) and short acronyms (ECA, FC), except when the whole name was typed in capitals.
- A player's chosen alias (`aka`) is shown exactly as written.
- `nameInitials(name)` gives the placeholder for a team without a logo or a player without a photo.
- Forms always edit the stored value, never the displayed one.

## Layout

- Place each page inside `.league-page` with a `.section-header`, a concise title, and a short Spanish description.
- Keep browsing, statistics, and pending work visible. Put secondary editing, creation, and import forms inside native `.ui-disclosure` details with a `.ui-disclosure-body`.
- Keep permissions on their existing outer containers. A disclosure controls presentation; authorization is enforced by the server.
- Use gold for primary actions, outlined buttons for secondary actions, and red for destructive actions. Keep status labels as text, never colour alone.
- Keep input text at 16px and touch targets at least 44px. Prefer compact two-column metrics on mobile and preserve horizontal table scrolling with sticky team identity.
- Keep IDs and form names stable so page controllers remain compatible. Validation reveals closed action panels automatically.
- The shared layout marks the parent navigation section, gives collapsed icons accessible names, and returns keyboard focus when the mobile drawer closes.
- Honor reduced-motion preferences and retain the skip link and visible focus indicators.

## Session

`static/layout.js` asks `/api/auth/session` once per page and exposes the result as `window.flagtasticSession` (the user, or `null` for a visitor). Page scripts await it before calling private endpoints, so visitors never trigger `401` responses. `/api/auth/me` still answers `401` without a session and remains the endpoint for the mobile app.

## Visual guards

`tests/browser/visual_guards.cjs` renders the public pages (teams, games, standings, statistics, roster, login) through the real application with synthetic fixtures. It checks them at 320, 390, 768 and 1280 px. It fails on:

- a page that scrolls sideways;
- text cut off sideways;
- content escaping its card, or overlapping cards;
- broken images;
- league fonts that did not load;
- unexpected API requests;
- any script or console error.

CI uploads the screenshots as the `visual-guards` artifact. When a page gains a new API request, add a fixture for it. When a new page goes public, add it to `PAGES`.
