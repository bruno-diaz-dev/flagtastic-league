# FlagTastic interface conventions

Styles load in this order on every page: `static/tokens.css`, `static/style.css`, `static/ui.css`, `static/theme.css`, then any page stylesheet.

- `tokens.css` is the single source for colour, type and shape. Use its variables (`--color-*`, `--font-body`, `--font-display`, `--ui-radius*`, `--ui-gap`, `--ui-shadow`) instead of hard-coded values, and add a token there rather than a one-off colour in a page file.
- `ui.css` is the shared visual layer. `style.css` keeps the older functional layout rules.
- `theme.css` is the league broadcast theme: navigation shell, page bands, week tabs and scoreboard game rows. It restyles existing markup only, so IDs, form names and page scripts are unchanged.

## Navigation shell

- **Desktop (821 px and up):** the sidebar markup renders as a sticky top bar. It holds the logo and wordmark, the four public sections, a "Más" menu with the role tools, and the session controls. "Más" appears only once a role link is visible; it closes on outside click, Escape or focus leaving it.
- **Phones and tablets (820 px and below):**
  - The collapsed sidebar is a slim 56 px top bar with the logo and the page name.
  - A fixed bottom tab bar (`.tabbar`) links the four public sections and marks the current one. Its fifth tab, "Más" (`#tabbar-more`), opens the same sidebar as a bottom sheet.
  - The sheet shows the role tools as tiles and the session controls at its foot. The public sections are not repeated there.
  - The existing open and close behaviour still applies: Escape, the backdrop and the focus trap. Focus returns to "Más" when the sheet closes.
- Role links keep their IDs (`#dashboard-link`, `#admin-users-link`…). `layout.js` reveals them and the "Más" menu from the shared session.

## Page bands

`.league-page > .section-header` runs edge to edge under the top bar, with faint yard lines. Its text stays aligned with the page column: `layout.js` publishes `--scrollbar-width`, so the band never causes sideways scrolling. A page that opens with a `.back-link` keeps the link inside the band.

## Shared page system

The games page language applies to every page:

- **No "FlagTastic · …" kickers.** A band carries the page title, a short description and, where it helps, `#page-hero-tags` (for example the division on screen) and `#page-hero-stats` (large numbers). Page scripts fill them with `setPageHero({tags, stats})` from `static/page_ui.js`.
- **Filter bar (`.filter-bar`):** a slim sticky bar for division pickers and directory filters. It joins the band when it sits right under it. Label text is visually hidden but stays for screen readers.
- **Branch buttons:** `<select data-segmented="Rama">` renders as pill buttons. The select stays the source of truth, so page scripts and forms are unchanged. A required select's empty prompt is not offered as a button.
- **Auto-submit:** `<form data-auto-submit>` submits when one of its selects changes, so division filters need no "Consultar" button. The button stays, visually hidden, for keyboards.
- **Section titles** use the condensed face in uppercase. **Metrics** (`.stat-grid`) are a strip of large numbers, each with a rule on its left, not boxes.
- **Tool panels** (`.ui-disclosure`, `.ui-action-hub`) are slim gold bars. **Tables** read like scoreboards, with condensed numbers. **Cards** are flat rows with one border.
- **Teams directory:** grouped by division like the schedule (`.team-division`). **Leaders:** the first row stands out with a larger photo and number.

## Home page

`/` is the league front page (`templates/home.html`, `static/home.js`). The logo in the top bar links to it.

- **Band:** the next week with games to play (Hoy, Mañana, En N días), its date and venue, and how many games, fields and divisions it holds. With nothing scheduled, it names the last week played.
- **Próxima jornada:** the first six games still to play, in start-time order, with a link to the full calendar.
- **Últimos resultados:** the latest week played. Its featured score (the same pick as the games page) leads, followed by six more results.
- **Líderes por división:** a branch and category picker (Varonil · Libre by default) with the top five of the table and the number one of each statistic.

## Loading and empty states

`static/page_ui.js` loads in the head, so page scripts can use its helpers right away:

- `skeletonMarkup(shape, count, label)` is a loading placeholder shaped like the content: `"games"`, `"table"` or `"cards"`. Screen readers hear the label. Partidos, Tabla, Estadísticas, Equipos and the home page use it instead of "Cargando…".
- `emptyStateMarkup({icon, title, text, action})` is the shared empty state: an icon, a title, one line and, where there is a next step, a link (`{label, href}`) or a button (`{label, id}`). Icons: `calendar`, `trophy`, `chart`, `search`, `team`, `ball`, `alert`.

Page scripts check that a helper exists before using it, because the isolated browser and script tests load them without `page_ui.js`.

## Installable app

`/manifest.webmanifest` makes the site installable from the browser ("Agregar a pantalla de inicio"). It opens standalone on `/` with the league navy and the logo icons in `static/assets` (192, 512 and a maskable 512). iOS uses `apple-touch-icon.png`. There is no service worker, so nothing is cached offline and every visit gets current scores.

## Games page

- **Week band (`#games-hero`):** the header tells the story of the week on screen, either the selected week or, under "Próximos", the next week with games to play. It shows:
  - when it is played (Hoy, Mañana, En N días, Finalizada) and a "Día de finales" tag;
  - "Jornada N · Finales";
  - the date and venue;
  - games, fields, and finals or points;
  - the week number as a watermark.
- **Week tabs (`#games-week-strip`):** they sit on the band's bottom edge. A tab only sets the existing `#game-filter-week` select and fires its `change` event, so filters, counts and week actions behave as before.
- **Filter bar:** a slim bar that stays under the top bar. It holds the branch buttons (they drive `#game-filter-branch`), category, team search, the count and "Más filtros" (week, status, field).
- **Scoreboard rows:** each game is one row grouped under a large start time:
  - left: field, division or finals label;
  - centre: home team, score or "VS" with the time, away team;
  - right: a chevron.

  The whole row opens the game, and team names keep their roster links. A decided game marks the winning team (`data-outcome="winner"`). Unresolved bracket slots read "Por definir". Admin and scorekeeper panels fold under each row.
- **Width:** visitors get the standard 1200 px column. League administrators keep the wide layout for the schedule board.

The standings page opens on Varonil · Libre instead of an empty form.

## Live game

The live panel (`templates/live_game_panel.html`) on a game's page reads like a broadcast:

- **Scoreboard:** each team's logo (or initials), name and score. The centre shows the period and clock of the last confirmed play while live, and "Final" once the game is completed. The state pill pulses orange while live. On phones the scoreboard stays pinned under the top bar.
- **Timeline:** one compact row per play. It shows the minute and period, the play and its narrative, and small "Ver" and "Anular" actions. A coloured edge marks the kind of play (`data-kind-group`: score in gold, defense in blue, pauses muted).
- **Capture:** the referee controls keep their IDs and order. On phones the "Registrar jugada" footer stays above the tab bar while choosing players. Pauses, finishing and cancelling are grouped in matching panels.

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
