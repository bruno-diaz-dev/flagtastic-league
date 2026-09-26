"""Pydantic request contracts and league-wide input constraints."""

from datetime import time

from pydantic import BaseModel, Field, SecretStr, field_validator

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
        normalized = value.strip()
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


class PlayerCreate(BaseModel):
    """Validate a player registration for a team roster."""
    name: str = Field(min_length=1)
    curp: str = Field(min_length=18, max_length=18)
    age: int = Field(gt=0)
    jersey_number: int = Field(ge=0)

    @field_validator("curp")
    @classmethod
    def normalize_curp(cls, curp):
        """Keep representative-created identities claimable at registration."""
        return curp.strip().upper()

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


class PlayerAccountCreate(BaseModel):
    """Validate a self-service player account registration."""

    email: str = Field(min_length=3)
    password: SecretStr = Field(min_length=8)
    name: str = Field(min_length=1)
    aka: str | None = Field(default=None, max_length=80)
    curp: str = Field(min_length=18, max_length=18)
    age: int = Field(gt=0)

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


class TeamMembershipCreate(BaseModel):
    """Validate the jersey selected by a player joining a team."""

    jersey_number: int = Field(ge=0)


class PlayerProfileUpdate(BaseModel):
    """Validate player-editable public profile fields."""

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
