import os
import asyncio
import sys

from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient

load_dotenv()

TAVILY_API_KEY =os.getenv("TAVILY_API_KEY")
AVIATIONSTACK_API_KEY = os.getenv("AVIATIONSTACK_API_KEY")
AVIATIONSTACK_PYTHON = os.getenv(
    "AVIATIONSTACK_PYTHON",
    r"D:\GENAI\Multi_agent_MCP\aviationstack-mcp\.venv\Scripts\python.exe"
)
OPENWEATHER_API_KEY=os.getenv("OPENWEATHER_API_KEY")

client=MultiServerMCPClient(
{
    # Remote
    "tavily":{
        "transport":"streamable_http",
        "url":f"https://mcp.tavily.com/mcp/?tavilyApiKey={TAVILY_API_KEY}"
    },

     # Local MCP Server
    # "aviationstack":{
    #             "transport":"stdio",
    #             "command": r"D:\GENAI\Multi_agent_MCP\aviationstack-mcp\.venv\Scripts\python.exe",

    #                 "args":[
    #                 "-m",
    #                 "aviationstack_mcp",
    #                 "mcp",
    #                 "run"
    #             ],
    
    # "aviationstack":{
    #         "transport":"stdio",
    #         "command": sys.executable,
    #             "args":[
    #             "-m",
    #             "aviationstack_mcp",
    #             "mcp",
    #             "run"
    #         ],
    #             "env":{
    #                 "AVIATIONSTACK_API_KEY": AVIATIONSTACK_API_KEY 
    #             }
    #         },

    # "aviationstack": {
    # "transport": "stdio",
    # "command": AVIATIONSTACK_PYTHON,
    # "args": ["-m", "aviationstack_mcp", "mcp", "run"],
    # "env": {"AVIATIONSTACK_API_KEY": AVIATIONSTACK_API_KEY}
    # },

    # Custom MCP Server
    # "weather":{
    #             "transport":"stdio",
    #             "command":r"D:\GENAI\Multi_agent_MCP\Agent1\Scripts\python.exe",
    #             "args":[
    #                  r"D:\GENAI\Multi_agent_MCP\custom_weather_mcp.py"
    #             ],
    "weather":{
            "transport":"stdio",
            "command": sys.executable,
            "args":[
                os.path.join(os.path.dirname(__file__), "custom_weather_mcp.py")
            ],
                "env":{
                    "OPENWEATHER_API_KEY": OPENWEATHER_API_KEY
                }
            }
            

}

)

print("Weather script path:", os.path.join(os.path.dirname(__file__), "custom_weather_mcp.py"))
# async def main():

#    tools=await client.get_tools()

#    print("\nAvailables MCP Tools:\n")

#    for tool in tools:
#        print(tool.name)


# search_tool=None
# async def initialize_mcp():
#     global search_tool
#     if search_tool is not None:
#         return

#     tools=await client.get_tools()
#     print("\nAvailable MCP Tools:")

#     for tool in tools:
#         print(tool.name)


#     search_tool=next(
#         tool
#         for tool in tools
#         if tool.name=="tavily_search"
#     )



search_tool=None
aviation_tools={}

async def initialize_mcp():

    global search_tool
    global aviation_tools

    if search_tool is not None and aviation_tools:
        return


    tools = await client.get_tools()

    print("\nAvailable MCP Tools:\n")


    for tool in tools:
        print(tool.name)


    search_tool=next(
        tool
        for tool in tools
        if tool.name == "tavily_search"
    )

    aviation_tools={
        tool.name:tool
        for tool in tools
        if tool.name !="tavily_search"
    }




async def tavily_mcp_search(query:str):
    await initialize_mcp()
    result=await search_tool.ainvoke(
        {
            "query":query
        }
    )

    return result


async def aviation_mcp_call(
    tool_name: str,
    tool_args: dict = None
):

    tools = await client.get_tools()

    tool = next(
        t for t in tools
        if t.name == tool_name
    )

    result = await tool.ainvoke(
        tool_args or {}
    )

    return result



async def get_airports():

    await initialize_mcp()

    tool = aviation_tools.get("list_airports")

    if not tool:
        return "Airport tool unavailable"

    result = await tool.ainvoke({})

    return result


async def get_airlines():

    await initialize_mcp()

    tool = aviation_tools.get("list_airlines")

    if not tool:
        return "Airline tool unavailable"

    result = await tool.ainvoke({})

    return result


weather_tool=None
forecast_tool=None

async def initialize_weather_tools():

    global weather_tool,forecast_tool

    if weather_tool is not None:
        return

    tools=await client.get_tools()

    weather_tool=next((t for t in tools if t.name=="get_current_weather"),None)
    if not weather_tool:
        return "Wheather tool unavailable"

    forecast_tool = next((t for t in tools if t.name=="get_forecast"),None)
    if not forecast_tool:
        return "Forecast tool unavailable"

async def weather_mcp_search(city:str):

    await initialize_weather_tools()
    if not weather_tool:
        return  "Weather tool unavailable"

    return await weather_tool.ainvoke(
        {
            "city":city
        }
    )


async def forecast_mcp_search(city:str):

    await initialize_weather_tools()
    if not forecast_tool:
            return "Forecast tool unavailable"

    return await forecast_tool.ainvoke(
        {
            "city":city
        }
    )



from langchain_groq import ChatGroq

#LLM

llm=ChatGroq(
    model="llama-3.3-70b-versatile"
)

#######################################
# Destination Extractor
#######################################


def extract_destination(query:str):

    prompt=f"""
    Extract only the destination city or country.

    Query:
    {query}

    Return only destination name.
"""

    response= llm.invoke(prompt)

    return response.content.strip()

# async def main():
#     print("Starting Diagnostic...")
#     async with client:  # Crucial: Spawns sub-processes and sets up networks
#         await initialize_mcp()

async def main():
    print("Starting Diagnostic...")
    await initialize_mcp()
    print("MCP tools initialized successfully")


if __name__=="__main__":
    asyncio.run(main())