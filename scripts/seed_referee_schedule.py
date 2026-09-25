"""Seed development referee accounts used by the sample official role sheet."""

import secrets
import unicodedata

from models import UserCreate
from repositories.users import create_user, get_all_users, set_user_roles


OFFICIAL_NAMES = (
    "Cam", "Alan", "Miguel", "Allison", "Fabian", "Heiman", "Micky",
    "Roy", "Areli", "Tony", "Jaquie", "Mateo", "Pada", "Angel",
    "Cabrerita", "Zoe", "Brucie", "Alex", "Eli B", "Peloy", "China",
    "Blanky", "Vicky", "Gloria", "Fer", "Moy", "KC", "Jimmy",
    "Woodson", "Sariel"
)


def _normalized(value):
    text = unicodedata.normalize("NFKD", value)
    return "".join(char for char in text if not unicodedata.combining(char)).casefold()


def _email_slug(name):
    return "".join(char for char in _normalized(name) if char.isalnum())


def seed_officials():
    """Create missing development identities and preserve all existing roles."""
    users = get_all_users()
    by_display_name = {
        _normalized(user.get("display_name") or user["name"]): user
        for user in users
    }
    seeded = []
    for name in OFFICIAL_NAMES:
        user = by_display_name.get(_normalized(name))
        if user is None:
            user = create_user(UserCreate(
                email=f"official.{_email_slug(name)}@flagtastic.local",
                name=name,
                password=secrets.token_urlsafe(24),
                role="referee"
            ))
        elif "referee" not in user.get("roles", [user["role"]]):
            user = set_user_roles(user["id"], set(user["roles"]) | {"referee"})
        seeded.append(user)
    return seeded


if __name__ == "__main__":
    officials = seed_officials()
    print(f"{len(officials)} oficiales disponibles para pruebas.")
