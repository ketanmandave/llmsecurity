from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_workspace_user
from app.core.config import settings
from app.database.session import get_db
from app.models.user import User
from app.schemas.workspace import ChatMessageRequest, ChatMessageResponse, ConversationDetail, ConversationOut
from app.services.conversation_service import ConversationService
from app.gateway.context import RequestContext
from app.gateway.service import AsyncProviderResult, GatewayError, SentinelAIGateway
from app.rag.auth.jwt import principal_from_user
from app.rag.integration.conversation import answer_conversation_question

router = APIRouter()


@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations(user: User = Depends(get_workspace_user), db: Session = Depends(get_db)) -> list[ConversationOut]:
    return ConversationService(db).list_for_session(user.id)


@router.post("/conversations", response_model=ConversationOut, status_code=status.HTTP_201_CREATED)
def create_conversation(user: User = Depends(get_workspace_user), db: Session = Depends(get_db)) -> ConversationOut:
    return ConversationService(db).create(user.id)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(conversation_id: str, user: User = Depends(get_workspace_user), db: Session = Depends(get_db)) -> ConversationDetail:
    conversation = ConversationService(db).get_for_session(conversation_id, user.id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return conversation


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(conversation_id: str, user: User = Depends(get_workspace_user), db: Session = Depends(get_db)) -> None:
    conversations = ConversationService(db)
    conversation = conversations.get_for_session(conversation_id, user.id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    conversations.delete(conversation)


@router.post("/conversations/{conversation_id}/messages", response_model=ChatMessageResponse)
async def send_message(conversation_id: str, payload: ChatMessageRequest, user: User = Depends(get_workspace_user), db: Session = Depends(get_db)) -> ChatMessageResponse:
    """Run assistant or secured company-knowledge mode in one conversation."""

    conversations = ConversationService(db)
    conversation = conversations.get_for_session(conversation_id, user.id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    request_id = uuid4()
    user_message = conversations.add_message(
        conversation,
        "user",
        payload.content,
        mode=payload.mode,
        request_id=str(request_id),
    )
    history = [{"role": message.role, "content": message.content} for message in conversation.messages]
    context = RequestContext(
        request_id=str(request_id),
        conversation_id=conversation.id,
        user_id=user.id,
        role=user.role.name,
        prompt=payload.content,
        timestamp=datetime.now(timezone.utc),
        provider="groq-rag" if payload.mode == "rag" else settings.assistant_provider,
        metadata={"mode": payload.mode},
    )
    gateway = SentinelAIGateway(db=db)
    try:
        if payload.mode == "rag":
            principal = principal_from_user(user)

            async def rag_provider() -> AsyncProviderResult:
                result = await answer_conversation_question(
                    principal=principal,
                    question=payload.content,
                    conversation_id=conversation.id,
                    request_id=UUID(context.request_id),
                    document_ids=payload.document_ids,
                )
                return AsyncProviderResult(
                    content=result.answer,
                    metadata={
                        "citations": [
                            source.model_dump(mode="json") for source in result.sources
                        ],
                        "grounded": result.grounded,
                        "model": result.model,
                    },
                )

            secured = await gateway.process_async_request(context, rag_provider)
            response = secured.content
            citations = secured.metadata.get("citations", [])
            grounded = secured.metadata.get("grounded")
            model = secured.metadata.get("model")
        else:
            response = gateway.process_request(context, history)
            citations = []
            grounded = None
            model = settings.assistant_model
    except GatewayError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    assistant_message = conversations.add_message(
        conversation,
        "assistant",
        response,
        mode=payload.mode,
        citations=citations,
        request_id=str(request_id),
        grounded=grounded,
        model=model,
    )
    return ChatMessageResponse(user_message=user_message, assistant_message=assistant_message)
