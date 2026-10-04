# FlagTastic interface conventions

`static/ui.css` is the shared visual layer, loaded after the existing functional layout styles. Use its color, radius, gap, hero, and shadow tokens for new pages instead of creating another page-specific theme.

- Place each page inside `.league-page` with a `.section-header`, a concise title, and a short Spanish description.
- Keep browsing, statistics, and pending work visible. Put secondary editing, creation, and import forms inside native `.ui-disclosure` details with a `.ui-disclosure-body`.
- Keep permissions on their existing outer containers. A disclosure controls presentation; authorization is enforced by the server.
- Use gold for primary actions, outlined buttons for secondary actions, and red for destructive actions. Keep status labels as text, never color alone.
- Keep input text at 16px and touch targets at least 44px. Prefer compact two-column metrics on mobile and preserve horizontal table scrolling with sticky team identity.
- Keep IDs and form names stable so page controllers remain compatible. Validation reveals closed action panels automatically.
- The shared layout marks the parent navigation section, gives collapsed icons accessible names, and returns keyboard focus when the mobile drawer closes.
- Honor reduced-motion preferences and retain the skip link and visible focus indicators.

Before merging a structural UI change, run the page-contract and navigation tests alongside the full application suite. Record separately whether a real-browser visual review was possible.
