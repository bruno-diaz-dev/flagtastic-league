"""Create the first league administrator from a trusted local terminal."""

import argparse
from getpass import getpass

from models import UserCreate
from repositories.users import create_user, get_user_by_email, update_user_role


def main():
    parser = argparse.ArgumentParser(description="Create a league administrator")
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    arguments = parser.parse_args()

    # Bootstrap commands run only from a trusted local terminal. Reusing an
    # existing account preserves its password and linked player identity.
    existing_user = get_user_by_email(arguments.email)
    if existing_user is not None:
        user = update_user_role(existing_user["id"], "league_admin")
        print(f"Administrador actualizado: {user['email']}")
        return

    password = getpass("Contraseña (mínimo 8 caracteres): ")
    confirmation = getpass("Confirma la contraseña: ")
    if password != confirmation:
        raise SystemExit("Las contraseñas no coinciden")

    user = create_user(UserCreate(
        email=arguments.email,
        name=arguments.name,
        password=password,
        role="league_admin"
    ))
    print(f"Administrador creado: {user['email']}")


if __name__ == "__main__":
    main()
