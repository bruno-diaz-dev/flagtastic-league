"""Deterministic projection of the league's live statistics sheet."""

POINTS = {"touchdown": 6, "passing_touchdown": 6, "extra_one": 1, "extra_two": 2, "safety": 2}
KINDS = {
    "pass_complete", "pass_incomplete", "passing_touchdown", "touchdown",
    "extra_one", "extra_two", "safety", "sack", "flag", "interception",
    "attendance", "note", "halftime", "two_minute_warning",
}
METRICS = ("points", "receptions", "interceptions", "sacks", "tackles", "passes_completed", "passes_attempted")


def project_events(events, home_id, away_id):
    """Rebuild scores and player totals; voided entries never contribute."""
    scores = {home_id: 0, away_id: 0}
    players = {}

    def player(team_id, player_id):
        if player_id is None:
            return None
        return players.setdefault((team_id, player_id), {
            "team_id": team_id, "player_id": player_id,
            **dict.fromkeys(METRICS, 0),
            "passing_points": 0,
        })

    for event in events:
        if event.get("voided_at"):
            continue
        team_id, kind = event["team_id"], event["kind"]
        if kind in ("attendance", "note", "halftime", "two_minute_warning"):
            continue
        actor = player(team_id, event.get("player_id"))
        receiver = player(team_id, event.get("receiver_id"))
        points = POINTS.get(kind, 0)
        if team_id in scores:
            scores[team_id] += points
        if kind in ("pass_complete", "pass_incomplete", "passing_touchdown") and actor:
            actor["passes_attempted"] += 1
            if kind != "pass_incomplete":
                actor["passes_completed"] += 1
                if receiver:
                    receiver["receptions"] += 1
            if kind == "passing_touchdown":
                actor["passing_points"] += 6
        if kind == "passing_touchdown" and receiver:
            receiver["points"] += points
        elif points and actor:
            actor["points"] += points
        metric = {"sack": "sacks", "flag": "tackles", "interception": "interceptions"}.get(kind)
        if metric and actor:
            actor[metric] += 1
    return scores, list(players.values())
