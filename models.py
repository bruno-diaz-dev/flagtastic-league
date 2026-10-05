"""Pydantic request contracts and league-wide input constraints."""

from datetime import date, time
from typing import Literal

from pydantic import BaseModel, Field, SecretStr, field_validator, model_validator

from services.curp import resolve_player_identity

ALLOWED_BRANCHES = {
    "varonil",
    "femenil",
    "mixto"
}

ALLOWED_CATEGORIES = {
    "u6",
    "u8",
    "u10",
    "u12",
    "u14",
    "u16",
    "u18",
    "libre"
}

ALLOWED_USER_ROLES = {
    "league_admin",
    "team_representative",
    "player",
    "referee"
}

ALLOWED_TEAM_STATUSES = {"pending", "active", "inactive"}

OFFICIAL_POSITIONS = {
    "referee",
    "down_judge",
    "field_judge",
    "side_judge",
    "statistician"
}

class TeamCreate(BaseModel):
    """Validate and normalize a team registration request."""
    name: str = Field(min_length=1)
    branch: str = Field(min_length=1)
    category: str = Field(min_length=1)
    head_coach: str | None = Field(default=None, max_length=120)
    coach: str | None = Field(default=None, max_length=120)
    manager: str | None = Field(default=None, max_length=120)

    @field_validator("name")
    @classmethod
    def normalize_team_name(cls, value):
        # Preserve intentional brand casing while removing whitespace variants
        # that must not create a second identity in the same division.
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("Team name is required")
        return normalized

    @field_validator("head_coach", "coach", "manager")
    @classmethod
    def normalize_team_staff(cls, value):
        normalized = value.strip() if value is not None else ""
        return normalized or None

    @field_validator("branch")
    @classmethod
    def validate_branch(cls, branch):
        normalized_branch = branch.strip().lower()

        if normalized_branch not in ALLOWED_BRANCHES:
            raise ValueError("Invalid branch")
        
        return normalized_branch

    @field_validator("category")
    @classmethod
    def validate_category(cls, category):
        normalized_category = category.strip().lower()

        if normalized_category not in ALLOWED_CATEGORIES:
            raise ValueError("Invalid category")

        return normalized_category

    @model_validator(mode="after")
    def normalize_youth_branch(self):
        """Store new U8-U12 teams in one compatible canonical branch."""
        if self.category in {"u8", "u10", "u12"}:
            self.branch = "mixto"
        return self

class TeamStaffUpdate(BaseModel):
    """Validate the staff names displayed on a public roster."""

    head_coach: str | None = Field(default=None, max_length=120)
    coach: str | None = Field(default=None, max_length=120)
    manager: str | None = Field(default=None, max_length=120)

    @field_validator("head_coach", "coach", "manager")
    @classmethod
    def normalize_staff_name(cls, value):
        normalized = value.strip() if value is not None else ""
        return normalized or None


class TeamStatusUpdate(BaseModel):
    """Validate a league-controlled team lifecycle transition."""

    status: str = Field(min_length=1)

    @field_validator("status")
    @classmethod
    def validate_status(cls, status):
        normalized = status.strip().lower()
        if normalized not in ALLOWED_TEAM_STATUSES:
            raise ValueError("Invalid team status")
        return normalized


class TeamNameUpdate(BaseModel):
    """Validate an administrator correction to a team's public name."""

    name: str = Field(min_length=1, max_length=120)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, name):
        normalized = " ".join(name.split())
        if not normalized:
            raise ValueError("Team name cannot be empty")
        return normalized


class PlayerCreate(BaseModel):
    """Validate a player registration for a team roster."""
    name: str = Field(min_length=1)
    curp: str = Field(min_length=1, max_length=18)
    identity_type: Literal["curp", "provisional"] = "curp"
    birth_date: date | None = None
    age: int | None = Field(default=None, gt=0)
    jersey_number: int = Field(ge=0)

    @field_validator("curp")
    @classmethod
    def normalize_curp(cls, curp):
        """Keep representative-created identities claimable at registration."""
        return curp.strip().upper()

    @model_validator(mode="after")
    def derive_completed_age(self):
        """Prefer CURP-derived completed age while accepting legacy test data."""
        self.birth_date, self.age = resolve_player_identity(
            self.curp, self.identity_type, self.birth_date, self.age
        )
        return self


class RosterPlayerUpdate(PlayerCreate):
    """Validate identity and jersey corrections for an active membership."""

class GameCreate(BaseModel):
    """Validate the two participants of a new game."""
    home_team_id: int = Field(gt=0)
    away_team_id: int = Field(gt=0)
    week: int = Field(default=1, gt=0)
    field_number: int = Field(ge=1, le=8)
    start_time: time | None = None

class GameScoreUpdate(BaseModel):
    """Validate a non-negative final score update."""
    home_score: int = Field(ge=0)
    away_score: int = Field(ge=0)


class GameStatusUpdate(BaseModel):
    """Administrator-controlled state for an unplayed game."""

    status: Literal["scheduled", "postponed"]


class UserCreate(BaseModel):
    """Validate and normalize a new application user."""
    email: str = Field(min_length=3)
    name: str = Field(min_length=1)
    password: str = Field(min_length=8)
    role: str = Field(min_length=1)

    @field_validator("email")
    @classmethod
    def validate_email(cls, email):
        normalized_email = email.strip().lower()

        if "@" not in normalized_email or "." not in normalized_email:
            raise ValueError("Invalid email")

        return normalized_email

    @field_validator("role")
    @classmethod
    def validate_role(cls, role):
        normalized_role = role.strip().lower()

        if normalized_role not in ALLOWED_USER_ROLES:
            raise ValueError("Invalid role")

        return normalized_role

class LoginRequest(BaseModel):
    """Validate credentials submitted to the login endpoint."""

    email: str = Field(min_length=3)
    password: SecretStr

    @field_validator("email")
    @classmethod
    def validate_email(cls, email):
        normalized_email = email.strip().lower()

        if "@" not in normalized_email or "." not in normalized_email:
            raise ValueError("Invalid email")

        return normalized_email


class PasswordChange(BaseModel):
    """Validate a replacement password for an authenticated account."""

    current_password: SecretStr
    new_password: SecretStr = Field(min_length=8)


class PasswordResetRequest(BaseModel):
    """Validate a public password reset request without account disclosure."""

    email: str = Field(min_length=3)

    @field_validator("email")
    @classmethod
    def validate_email(cls, email):
        normalized = email.strip().lower()
        if "@" not in normalized or "." not in normalized:
            raise ValueError("Invalid email")
        return normalized


class PasswordResetConfirmation(BaseModel):
    """Validate a one-time reset token and replacement password."""

    token: str = Field(min_length=32, max_length=200)
    new_password: SecretStr = Field(min_length=8)


class PlayerAccountCreate(BaseModel):
    """Validate a self-service player account registration."""

    email: str = Field(min_length=3)
    password: SecretStr = Field(min_length=8)
    name: str = Field(min_length=1)
    aka: str | None = Field(default=None, max_length=80)
    curp: str = Field(min_length=1, max_length=18)
    identity_type: Literal["curp", "provisional"] = "curp"
    birth_date: date | None = None
    age: int | None = Field(default=None, gt=0)

    @field_validator("email")
    @classmethod
    def validate_email(cls, email):
        normalized_email = email.strip().lower()
        if "@" not in normalized_email or "." not in normalized_email:
            raise ValueError("Invalid email")
        return normalized_email

    @field_validator("curp")
    @classmethod
    def normalize_curp(cls, curp):
        return curp.strip().upper()

    @field_validator("aka")
    @classmethod
    def normalize_aka(cls, aka):
        normalized = aka.strip() if aka is not None else ""
        return normalized or None

    @model_validator(mode="after")
    def derive_completed_age(self):
        """Use completed years of age from the CURP for account matching."""
        self.birth_date, self.age = resolve_player_identity(
            self.curp, self.identity_type, self.birth_date, self.age
        )
        return self


class TeamMembershipCreate(BaseModel):
    """Validate the jersey selected by a player joining a team."""

    jersey_number: int = Field(ge=0)


class RegisteredPlayerMembershipCreate(BaseModel):
    """Validate a jersey assigned by a manager to an existing account."""

    player_id: int = Field(gt=0)
    jersey_number: int = Field(ge=0)


class PlayerProfileUpdate(BaseModel):
    """Validate player-editable public profile fields."""

    aka: str | None = Field(default=None, max_length=80)

    @field_validator("aka")
    @classmethod
    def normalize_aka(cls, aka):
        normalized = aka.strip() if aka is not None else ""
        return normalized or None


class RefereeProfileUpdate(BaseModel):
    """Validate referee-editable public profile fields."""

    aka: str | None = Field(default=None, max_length=80)

    @field_validator("aka")
    @classmethod
    def normalize_aka(cls, aka):
        normalized = aka.strip() if aka is not None else ""
        return normalized or None


class UserRoleUpdate(BaseModel):
    """Validate a role selected by a league administrator."""

    role: str = Field(min_length=1)

    @field_validator("role")
    @classmethod
    def validate_role(cls, role):
        normalized_role = role.strip().lower()
        if normalized_role not in ALLOWED_USER_ROLES:
            raise ValueError("Invalid role")
        return normalized_role


class UserRolesUpdate(BaseModel):
    """Validate the complete role set managed by a league administrator."""

    roles: set[str] = Field(min_length=1)

    @field_validator("roles")
    @classmethod
    def validate_roles(cls, roles):
        normalized = {role.strip().lower() for role in roles}
        if not normalized or not normalized.issubset(ALLOWED_USER_ROLES):
            raise ValueError("Invalid roles")
        return normalized


class StaffAccountCreate(BaseModel):
    """Validate an administrator-created account without player identity."""

    email: str = Field(min_length=3)
    name: str = Field(min_length=1)
    password: SecretStr = Field(min_length=8)
    roles: set[str] = Field(min_length=1)

    @field_validator("email")
    @classmethod
    def validate_email(cls, email):
        normalized = email.strip().lower()
        if "@" not in normalized or "." not in normalized:
            raise ValueError("Invalid email")
        return normalized

    @field_validator("roles")
    @classmethod
    def validate_roles(cls, roles):
        normalized = {role.strip().lower() for role in roles}
        staff_roles = ALLOWED_USER_ROLES - {"player"}
        if not normalized or not normalized.issubset(staff_roles):
            raise ValueError("Invalid staff roles")
        return normalized


class GameOfficialAssignment(BaseModel):
    """Pair one official account with its position in a game."""

    user_id: int = Field(gt=0)
    position: str = Field(min_length=1)

    @field_validator("position")
    @classmethod
    def validate_position(cls, position):
        normalized = position.strip().lower()
        if normalized not in OFFICIAL_POSITIONS:
            raise ValueError("Invalid official position")
        return normalized


class OfficialPositionUpdate(BaseModel):
    """Validate the position selected for a manual assignment."""

    position: str = Field(min_length=1)

    @field_validator("position")
    @classmethod
    def validate_position(cls, position):
        normalized = position.strip().lower()
        if normalized not in OFFICIAL_POSITIONS:
            raise ValueError("Invalid official position")
        return normalized


class RefereeScheduleAssignment(BaseModel):
    """Validate one administrator-reviewed row from schedule OCR."""

    game_id: int = Field(gt=0)
    field_number: int = Field(ge=1, le=8)
    scheduled_time: time | None = None
    officials: list[GameOfficialAssignment] = Field(default_factory=list)


class RefereeScheduleConfirmation(BaseModel):
    """Validate the complete set of reviewed schedule assignments."""

    assignments: list[RefereeScheduleAssignment] = Field(min_length=1)


class GameScheduleOcrWord(BaseModel):
    """One OCR word and its bounding box from browser-side recognition."""

    text: str = Field(min_length=1, max_length=120)
    left: int = Field(ge=0)
    top: int = Field(ge=0)
    width: int = Field(ge=0)
    height: int = Field(ge=0)


class GameScheduleOcrCellRow(BaseModel):
    field_number: int = Field(ge=1, le=6)
    start_time: time | None = None
    home_team: str = Field(min_length=1, max_length=160)
    away_team: str = Field(min_length=1, max_length=160)


class GameScheduleOcrCellsPayload(BaseModel):
    week: int = Field(gt=0, le=99)
    rows: list[GameScheduleOcrCellRow] = Field(min_length=1, max_length=500)


class GameScheduleOcrPayload(BaseModel):
    """Validate browser OCR output before matching it to league teams."""

    image_width: int = Field(gt=0, le=20000)
    image_height: int = Field(gt=0, le=20000)
    recognized_text: str | None = Field(default=None, max_length=50000)
    week_override: int | None = Field(default=None, gt=0, le=99)
    words: list[GameScheduleOcrWord] = Field(min_length=1, max_length=10000)


class GameScheduleImportRow(GameCreate):
    """Validate one administrator-reviewed game from a schedule file."""


class GameScheduleImportConfirmation(BaseModel):
    """Validate a reviewed batch before it is persisted atomically."""

    games: list[GameScheduleImportRow] = Field(min_length=1, max_length=500)
