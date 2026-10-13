"""Original upload names match registered names without guessing identities."""
from services.team_matching import match_team_name


def test_joined_registered_name_with_division_tokens_matches_original_label():
    teams = [
        {'id': 133, 'name': 'SelAgsFemU14', 'branch': 'femenil', 'category': 'libre'},
        {'id': 2, 'name': 'SelAgsFemU14', 'branch': 'femenil', 'category': 'u14'},
        {'id': 3, 'name': 'SelAgsVarU14', 'branch': 'varonil', 'category': 'libre'},
    ]
    assert match_team_name('Sel Ags U14', teams, 'femenil', 'libre')['id'] == 133


def test_joined_names_do_not_resolve_ambiguous_teams_or_cross_divisions():
    teams = [
        {'id': 1, 'name': 'SelAgsFemU14', 'branch': 'femenil', 'category': 'libre'},
        {'id': 2, 'name': 'Sel Ags', 'branch': 'femenil', 'category': 'libre'},
    ]
    assert match_team_name('Sel Ags U14', teams, 'femenil', 'libre') is None
    assert match_team_name('Sel Ags U14', teams, 'varonil', 'libre') is None
    assert match_team_name('Sel Ags U14', teams, 'femenil', 'u14') is None
