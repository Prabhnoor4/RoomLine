from contextlib import asynccontextmanager

from fastapi import FastAPI
from langchain_core.messages import HumanMessage

from app.agent.graph import graph
from app.db import engine, init_db
from app.schemas import ChatRequest, ChatResponse

# used to create the db on startup- does nothing if already exists
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await engine.dispose()


app= FastAPI(lifespan=lifespan)


def extract_reply_text(content) -> str:
    # Some models (reasoning models especially) return content as a list of
    # labeled blocks (e.g. "thinking" + "text") instead of a plain string.
    # We only want the actual answer meant for the guest, not its internal reasoning.
    if isinstance(content, str):
        return content

    text_blocks = [block["text"] for block in content if isinstance(block, dict) and block.get("type") == "text"]
    return "".join(text_blocks)


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    config = {
        "configurable": {
            "room_number": request.room_number,
            "thread_id": request.room_number,
        }
    }
    result = await graph.ainvoke(
        {"messages": [HumanMessage(content=request.message)]}, # this part goes to the AgentState which then goes to the graph
        config=config,
    )
    reply = extract_reply_text(result["messages"][-1].content)
    return ChatResponse(reply=reply)




@app.get("/health")
def health():
    return {"health": "The api is working fine"}
