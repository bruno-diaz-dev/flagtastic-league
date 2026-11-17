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


def test_confirmed_valkirias_alias_selects_vikingos_blanco_only_in_femenil_u14():
    teams = [
        {'id': 77, 'name': 'Vikingos Blanco', 'branch': 'femenil', 'category': 'u14'},
        {'id': 76, 'name': 'Vikingos Azul', 'branch': 'femenil', 'category': 'u14'},
        {'id': 5, 'name': 'Valkirias Blanco', 'branch': 'femenil', 'category': 'u12'},
        {'id': 6, 'name': 'Valkirias Blanco', 'branch': 'varonil', 'category': 'u14'},
    ]
    assert match_team_name('Valkirias Blanco', teams, 'femenil', 'u14')['id'] == 77
    assert match_team_name('VALKIRIAS BLANCO', teams, 'femenil', 'u14')['id'] == 77
    assert match_team_name('Valkirias Blanco', teams, 'femenil', 'u12')['id'] == 5
    assert match_team_name('Valkirias Blanco', teams, 'varonil', 'u14')['id'] == 6


def test_confirmed_alias_rejects_missing_or_ambiguous_target():
    blue = {'id': 76, 'name': 'Vikingos Azul', 'branch': 'femenil', 'category': 'u14'}
    white = {'id': 77, 'name': 'Vikingos Blanco', 'branch': 'femenil', 'category': 'u14'}
    assert match_team_name('Valkirias Blanco', [blue], 'femenil', 'u14') is None
    assert match_team_name('Valkirias Blanco', [white, {**white, 'id': 99}], 'femenil', 'u14') is None


def test_registered_literal_source_identity_still_takes_precedence_over_an_alias():
    teams = [
        {'id': 77, 'name': 'Vikingos Blanco', 'branch': 'femenil', 'category': 'u14'},
        {'id': 99, 'name': 'Valkirias Blanco', 'branch': 'femenil', 'category': 'u14'},
    ]
    assert match_team_name('Valkirias Blanco', teams, 'femenil', 'u14')['id'] == 99
