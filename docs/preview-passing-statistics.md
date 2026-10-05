# Preview: illustrative passing statistics

Preview only; do not merge or promote to production.

The visualization lives exclusively on /statistics. It reads published player_week_stats passing totals using the selected division, includes imported statistics, and offers a passer selector. The field uses 40 decorative markers to approximate the completion proportion, never individual throw locations. The curve is decorative. The UI explicitly states that locations and distances are not measured.

Live coverage and the referee capture form retain their production behavior. No coordinate capture, new database columns, live events, or extra capture steps are required. The previous optional-location prototype is removed from this branch. The unused nullable column previously added to the preview database is left intact to avoid discarding any experimental data; this version never reads or writes it.
