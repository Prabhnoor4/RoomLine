from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app import config
from app.agent.graph import workflow
from app.db import engine, init_db
from app.hotel_config import load_hotel_config
from app.schemas import ChatRequest, ChatResponse
from app.staff import router as staff_router

from langfuse import Langfuse
from langfuse.langchain import CallbackHandler 

Langfuse()
langfuse_handler=CallbackHandler()

# The graph gets compiled once the app starts (see lifespan below), since
# AsyncSqliteSaver needs an async setup step that can't run at plain import time.
graph = None


# used to create the db on startup- does nothing if already exists
@asynccontextmanager
async def lifespan(app: FastAPI):
    global graph
    await init_db()
    async with AsyncSqliteSaver.from_conn_string(config.CHECKPOINT_DB_PATH) as checkpointer:
        graph = workflow.compile(checkpointer=checkpointer)
        yield
    await engine.dispose()


app= FastAPI(lifespan=lifespan)
app.include_router(staff_router)


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
    run_config = {
        "configurable": {
            "room_number": request.room_number,
            "thread_id": request.room_number,
        },
        "callbacks":[langfuse_handler],
    }
    result = await graph.ainvoke(
        {"messages": [HumanMessage(content=request.message)]}, # this part goes to the AgentState which then goes to the graph
        config=run_config,
    )
    reply = extract_reply_text(result["messages"][-1].content)
    return ChatResponse(reply=reply)




@app.get("/health")
def health():
    return {"health": "The api is working fine"}


@app.get("/hotel-config")
def hotel_config():
    # Single source of truth for hotel branding/content - both frontend
    # pages fetch this instead of keeping their own hardcoded copy, so
    # editing this one file is enough to update the AI's prompt AND
    # what guests/staff see on the page.
    return load_hotel_config()


# Serves the frontend folder as plain files. Registered last so it doesn't
# swallow the API routes above - Starlette checks routes in the order they
# were added, and this one matches almost anything.
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
