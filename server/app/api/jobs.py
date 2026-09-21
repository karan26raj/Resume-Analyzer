from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user
from app.models.user import User


router = APIRouter(
    prefix="/jobs",
    tags=["Jobs"]
)


@router.get("/")
def get_jobs(
    current_user: User = Depends(get_current_user)
):
    return {
        "message": "Authenticated request",
        "user_id": current_user.id
    }