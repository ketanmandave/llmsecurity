from pydantic import BaseModel


class PermissionOut(BaseModel):
    id: int
    name: str
    description: str | None = None

    class Config:
        from_attributes = True
