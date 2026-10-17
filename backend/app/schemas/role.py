from pydantic import BaseModel


class RoleBase(BaseModel):
    name: str
    description: str | None = None


class RoleCreate(RoleBase):
    pass


class RoleOut(RoleBase):
    id: int

    class Config:
        from_attributes = True
