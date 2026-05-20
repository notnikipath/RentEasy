from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from shared.renteasy_common import (
    ChatMessage,
    ChatMessageRequest,
    Role,
    Settings,
    ViewingRecord,
    ViewingRequest,
    has_permission,
)

settings = Settings(service_name="chat-service", service_port=8405)
app = FastAPI(title="RentEasy Chat Service", version="1.0.0")


class ChatbotRequest(BaseModel):
    user_id: str
    prompt: str = Field(min_length=3, max_length=500)


ChatbotRequest.model_rebuild()


messages: list[ChatMessage] = [
    ChatMessage(
        message_id="MSG-SEED-1",
        conversation_id="CONV-APT-001",
        listing_id="LIST-DEMO-APT",
        sender_id="HOST-001",
        recipient_id="TENANT-100",
        text="Здравствуйте! Квартира доступна с 20 мая, могу показать в выходные.",
    )
]
viewings: list[ViewingRecord] = []


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.post("/chats/messages")
async def send_message(request: ChatMessageRequest) -> dict[str, Any]:
    if not has_permission(request.actor_role, "chat:send"):
        raise HTTPException(status_code=403, detail="Forbidden")

    item = ChatMessage(
        message_id=str(uuid4()),
        conversation_id=request.conversation_id,
        listing_id=request.listing_id,
        sender_id=request.sender_id,
        recipient_id=request.recipient_id,
        text=request.text,
    )
    messages.append(item)
    return item.model_dump(mode="json")


@app.get("/chats/{conversation_id}")
async def get_conversation(conversation_id: str, actor_role: Role = Role.TENANT) -> dict[str, Any]:
    if not has_permission(actor_role, "chat:read") and actor_role not in {Role.TENANT, Role.HOST}:
        raise HTTPException(status_code=403, detail="Forbidden")
    items = [item.model_dump(mode="json") for item in messages if item.conversation_id == conversation_id]
    items.sort(key=lambda item: item["created_at"])
    return {"conversation_id": conversation_id, "items": items, "count": len(items)}


@app.post("/viewings/request")
async def request_viewing(request: ViewingRequest) -> dict[str, Any]:
    if request.actor_role not in {Role.TENANT, Role.MANAGER, Role.ADMIN}:
        raise HTTPException(status_code=403, detail="Forbidden")

    item = ViewingRecord(
        viewing_id=str(uuid4()),
        listing_id=request.listing_id,
        user_id=request.user_id,
        host_id=request.host_id,
        desired_datetime=request.desired_datetime,
        note=request.note,
        status="pending",
    )
    viewings.append(item)
    return item.model_dump(mode="json")


@app.get("/viewings")
async def list_viewings(host_id: str | None = None, user_id: str | None = None) -> dict[str, Any]:
    items = [
        item.model_dump(mode="json")
        for item in viewings
        if (not host_id or item.host_id == host_id) and (not user_id or item.user_id == user_id)
    ]
    items.sort(key=lambda item: item["desired_datetime"])
    return {"items": items, "count": len(items)}


@app.post("/chatbot/match")
async def chatbot_match(request: ChatbotRequest) -> dict[str, Any]:
    prompt = request.prompt.lower()
    suggestions = []

    if "офис" in prompt or "коммер" in prompt:
        suggestions.append("Рекомендуем посмотреть LIST-DEMO-OFFICE в центре города.")
    if "посуточ" in prompt or "коротк" in prompt:
        suggestions.append("Для короткого проживания подходит LIST-DEMO-DAILY.")
    if "питом" in prompt or "кошка" in prompt or "собака" in prompt:
        suggestions.append("С животными можно в LIST-DEMO-APT.")

    if not suggestions:
        suggestions.append("Уточните город и бюджет, и я подберу варианты точнее.")

    return {"user_id": request.user_id, "suggestions": suggestions}
