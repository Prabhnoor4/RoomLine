from contextlib import asynccontextmanager

from fastapi import FastAPI
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app import config
from app.agent.graph import workflow
from app.db import engine, init_db
from app.schemas import ChatRequest, ChatResponse

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
        }
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
