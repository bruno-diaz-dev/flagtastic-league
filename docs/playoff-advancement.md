# Playoff advancement from imported schedules

The official calendar importer recognizes an empty `Final` or `3ro` team cell
as a pending bracket slot. Confirmation stores the slot and links it to the two
most recent same-division games before its scheduled time. When both feeder
games have completed scores, their winners fill a final and their losers fill
the third-place game automatically. The resulting fixtures use the time and
field from the imported slot.

Labels containing `Golden` or `Silver` divide four feeder games by field order:
the first two feed Golden, and the last two feed Silver. In the league's
confirmed bracket, those groups correspond to seeds 1–4 and 5–8. Unmarked
brackets use the two preceding same-division games.
