from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from app.api.dependencies import get_current_user

from app.models.user import User

from app.schemas.assistant import (
    AssistantQuestionRequest,
    AssistantQuestionResponse,
)

from app.services.rag import (
    ask_question,
    RAGServiceError,
)

router = APIRouter(
    prefix="/assistant",
    tags=["Assistant"]
)


@router.post(
    "/ask",
    response_model=AssistantQuestionResponse,
    status_code=status.HTTP_200_OK
)
def assistant_question(
    request: AssistantQuestionRequest,
    current_user: User = Depends(
        get_current_user
    ),
):
    try:

        answer, sources = ask_question(
            question=request.question,
            user_id=current_user.id,
            limit=request.limit,
        )

        return {
            "answer": answer,
            "sources": sources
        }

    except RAGServiceError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error)
        )