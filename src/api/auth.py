from fastapi import APIRouter, status

from domain.schemas import RegisterUserSchema

auth_router = APIRouter(prefix="/api/v1/auth", tags=["authorization"])


@auth_router.post("/register", status_code=status.HTTP_204_NO_CONTENT)
async def register_user(user: RegisterUserSchema) -> None:
    pass
