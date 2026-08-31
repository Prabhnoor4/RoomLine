from pydantic import BaseModel


class ChatRequest(BaseModel):
    room_number: str
    message: str


class ChatResponse(BaseModel):
    reply: str


class StatusUpdate(BaseModel):
    status: str
