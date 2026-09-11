from pydantic import BaseModel, Field, field_validator

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

class TeamCreate(BaseModel):
    name: str = Field(min_length=1)
    branch: str = Field(min_length=1)
    category: str = Field(min_length=1)

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


class PlayerCreate(BaseModel):
    name: str = Field(min_length=1)
    curp: str = Field(min_length=18, max_length=18)
    age: int = Field(gt=0)
    jersey_number: int = Field(ge=0, le=99)

class GameCreate(BaseModel):
    home_team_id: int = Field(gt=0)
    away_team_id: int = Field(gt=0)

class GameScoreUpdate(BaseModel):
    home_score: int = Field(ge=0)
    away_score: int = Field(ge=0)