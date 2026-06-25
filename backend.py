import logging
import traceback
from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import Any, cast
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from main import graph, DATABASE_URL

def extract_text(value) -> str:
    """Safely convert MCP content blocks or plain strings to str."""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(
            block["text"] for block in value 
            if isinstance(block, dict) and block.get("type") == "text"
        )
    return str(value) if value else ""

travel_agent = None
pool = None


@asynccontextmanager
async def lifespan(app):
    global travel_agent, pool
    pool = AsyncConnectionPool(
        conninfo=DATABASE_URL,
        max_size=10,
        kwargs={"autocommit": True},
        open=False
    )
    await pool.open()
    checkpointer = AsyncPostgresSaver(pool)
    await checkpointer.setup()
    travel_agent = graph.compile(checkpointer=checkpointer)
    print(">>> LIFESPAN DONE, travel_agent:", travel_agent)
    yield
    await pool.close()


class TravelRequest(BaseModel):
    query: str
    thread_id: str = "default_thread"


class TravelRespond(BaseModel):
    thread_id: str
    itinerary: str
    flight_results: str
    hotel_results: str
    weather_result: str
    llm_calls: int
    message_count: int


app = FastAPI(
    title="Travel Agent API",
    description="Multi_Agent Travel Planner",
    version='1.0.0',
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"status": "ok", "message": "Travel Agent API is running"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/plan", response_model=TravelRespond)
async def plan_travel(request: TravelRequest):
    global travel_agent
    print(">>> HIT /plan")
    if travel_agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized yet")

    print(">>> /plan called with:", request.query)
    config = {"configurable": {"thread_id": request.thread_id}}

    try:
        print(">>> calling ainvoke")
        result = await travel_agent.ainvoke(
            {
                "messages": [HumanMessage(content=request.query)],
                "user_query": request.query,
                "flight_results": "",
                "hotel_results": "",
                "weather_result": "",
                "itinerary": "",
                "llm_calls": 0,
            },
            config=cast(Any, config),
        )
        print(">>> ainvoke done")
    except BaseException as e:
        error_msg = traceback.format_exc()
        print(">>> EXCEPTION:", error_msg)
        raise HTTPException(status_code=500, detail=str(e))

    return TravelRespond(
    thread_id=request.thread_id,
    itinerary=extract_text(result.get("itinerary", "")),
    flight_results=extract_text(result.get("flight_results", "")),
    hotel_results=extract_text(result.get("hotel_results", "")),
    weather_result=extract_text(result.get("weather_result", "")),
    llm_calls=result.get("llm_calls", 0),
    message_count=len(result.get("messages", []))
)



@app.get("/history/{thread_id}")
def get_history(thread_id: str):
    global travel_agent
    if travel_agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized yet")
    config = {"configurable": {"thread_id": thread_id}}
    try:
        state = travel_agent.get_state(cast(Any, config))
        if state is None or state.values is None:
            raise HTTPException(status_code=404, detail="No history found for this thread_id")

        messages = state.values.get("messages", [])
        history = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                history.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                history.append({"role": "assistant", "content": msg.content})

        return {
            "thread_id": thread_id,
            "message_count": len(history),
            "messages": history,
            "itinerary": state.values.get("itinerary", "")
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error("FULL ERROR: %s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


# uvicorn backend:app --reload --port 8000