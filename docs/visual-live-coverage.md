Visual live coverage
====================

The match page renders a lightweight responsive SVG field from confirmed live events. There are no new capture fields, dependencies, endpoints, tracking coordinates or extra polling requests. Player and receiver jerseys identify the actors; the caption retains team, names, period and official clock.

Passes use a quadratic curve; rushing/return touchdowns use a straight route. Confirmed touchdowns show a six-point celebration. Defensive events, conversions, safety and match breaks have distinct labels. Existing statistics do not contain non-scoring runs, real locations, yardage or direction; the field explicitly labels every route illustrative rather than tracking data.

Initial loads show the latest valid play without automatically replaying history. A newly confirmed play animates once; refreshes preserve the current selection. Viewers can replay or select a play from the timeline. Voided plays and attendance never enter the field; invalidated selections fall back to the latest valid play. Pending local captures never animate publicly.

Animations are finite and suppressed for reduced-motion preferences or background documents. Static information remains available. SVG scales without raster assets or a game engine. Tests cover curve/line geometry, voided records, selection across refreshes, neutral moments, escaped identities and reduced motion; mobile Chromium verifies the integrated field and captures a touchdown screenshot.
