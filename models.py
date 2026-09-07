from pydantic import BaseModel, Field

class TeamCreate(BaseModel):
    name: str = Field(min_length=1)
    branch: str = Field(min_length=1)
    category: str = Field(min_length=1)

class PlayerCreate(BaseModel):
    name: str = Field(min_length=1)
    curp: str = Field(min_length=18, max_length=18)
    age: int = Field(gt=0)
    jersey_number: int = Field(ge=0, le=99)