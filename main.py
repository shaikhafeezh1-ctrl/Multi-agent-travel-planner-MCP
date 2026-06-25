import asyncio
asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
import os
from typing import TypedDict, Annotated, Any, cast
import operator
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool



from langgraph.graph import StateGraph , START , END
from langchain_core.messages import AnyMessage , HumanMessage , AIMessage , SystemMessage

from langchain_groq import ChatGroq


#from tools.tavily_tool import tavily_search
#from mcp_client import tavily_mcp_search
# from tools.flight_tools import search_flights
from mcp_client import (
    tavily_mcp_search,
    get_airlines,
    get_airports,
    aviation_mcp_call,extract_destination,forecast_mcp_search,weather_mcp_search
)

from dotenv import load_dotenv
load_dotenv()

llm=ChatGroq(
    model="llama-3.3-70b-versatile"
)

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL is None:
    raise ValueError("DATABASE_URL environment variable is not set")

class TravelState(TypedDict):
    messages : Annotated[list[AnyMessage], operator.add]
    user_query: str
    flight_results: str
    hotel_results: str
    weather_result: str
    itinerary: str
    llm_calls: int



# def flight_agent(state : TravelState):
#     query = state["user_query"]
#     #flight_data = search_flights(query)
#     return{
#         "flight_results": flight_data,
#         "messages":[
#             AIMessage(content=f"Flight result fetched")
#         ],
#         "llm_calls" : state.get("llm_calls",0) + 1
#     }


# Flight Agent
FLIGHT_AGENT_PROMPT = """
You are a travel flight expert.

User Query:
{query}

Airport Information:
{airport_data}

Airline Information:
{airline_data}

Generate:

1. Likely departure airport
2. Likely arrival airport
3. Airlines serving this route
4. Typical flight duration
5. Estimated airfare range
6. Peak season pricing warning
7. Booking advice

Return concise travel guidance.
"""



# Flight Agent
async def flight_agent(state: TravelState):
    print("\nINSIDE FLIGHT AGENT\n")

    query = state["user_query"]

    try:

        airports = await aviation_mcp_call("list_airports")
        

        airlines = await aviation_mcp_call("list_airlines")

        prompt = FLIGHT_AGENT_PROMPT.format(
            query=query,
            airport_data=str(airports)[:3000],
            airline_data=str(airlines)[:3000]
        )

        response = await llm.ainvoke([
            SystemMessage(
                content="You are an expert travel flight planner."
            ),
            HumanMessage(content=prompt)
        ])

        flight_data = response.content

    except Exception as e:

        flight_data = f"Flight information unavailable: {str(e)}"

    return {
        "flight_results": flight_data,
        "messages": [
            AIMessage(
                content="Flight recommendations generated"
            )
        ],
        "llm_calls": state.get("llm_calls", 0) + 1
    }

async def hotel_agent(state : TravelState):
    query = f'Best hotels for {state["user_query"]}'
    #hotal_result=tavily_search(query)

    hotal_result= await tavily_mcp_search(query)


    return {
        "hotel_results" : hotal_result,
        "messages" : [
            AIMessage(content="Hotel information fetched")
        ],
        "llm_calls" : state.get("llm_calls",0) + 1
    }


async def weather_agent(state : TravelState):

    city = extract_destination(state["user_query"])

    weather_data=await weather_mcp_search(city)

    forecast_data=await forecast_mcp_search(city)

    return {
        "weather_result":f"""
        Current weather:
        {weather_data}

        Forecast:
        {forecast_data}
        """,
        "messages":[
            AIMessage(content="Weather information fetched")
        ]
    }


async def itineary_agent(state : TravelState):

    prompt=f"""
    create a travel itineary.
    User query:
    {state["user_query"]}

    Flight Results:
    {state["flight_results"]}

    Hotel Result:
    {state["hotel_results"]}

    Weather Information:
    {state["weather_result"]}


"""

    response=await llm.ainvoke([
        SystemMessage(content="You are an expert travel agent"),
        HumanMessage(content=prompt)
    ])

    return{
        "itinerary":response.content,
        "messages":[response],
        "llm_calls":state.get("llm_calls",0)+1
    }




graph=StateGraph(TravelState)


graph.add_node("flight_agent",flight_agent)
graph.add_node("hotel_agent",hotel_agent)
graph.add_node("weather_agent",weather_agent)
graph.add_node("itineary_agent",itineary_agent)


graph.add_edge(START,"flight_agent")
graph.add_edge("flight_agent","hotel_agent")
graph.add_edge("hotel_agent","weather_agent")
graph.add_edge("weather_agent","itineary_agent")
graph.add_edge("itineary_agent",END)



# _conn = psycopg.connect(DATABASE_URL)
# _conn.autocommit = True
# checkpointer = PostgresSaver(_conn)
# checkpointer.setup()


_pool = AsyncConnectionPool(
    conninfo=DATABASE_URL,
    max_size=10,
    kwargs={"autocommit": True},
    open=False
)

async def setup():
    await _pool.open()
    checkpointer = AsyncPostgresSaver(_pool)  # pass pool, not connection
    await checkpointer.setup()
    return checkpointer
import nest_asyncio
nest_asyncio.apply()

checkpointer = asyncio.get_event_loop().run_until_complete(setup())



app=graph.compile(checkpointer=checkpointer)


# global config used when invoking the graph
config = {
    "configurable": {
        "thread_id": "user_hafeez"
    }
}

# For running standalone    
async def main():

    user_input = input("Enter travel request :")

    result = await app.ainvoke(
            {
                "messages": [HumanMessage(content=user_input)],
                "user_query": user_input,
                "flight_results": "",
                "hotel_results": "",
                "weather_result": "",
                "itinerary": "",
                "llm_calls": 0

            },

            config=cast(Any, config)

        )   

    print("\nFINAL RESPONSE:\n")

    for msg in result["messages"]:
        print(msg.content)

    try:

        await _pool.close()
    except Exception:
        pass


if __name__=="__main__":
    asyncio.run(main())

