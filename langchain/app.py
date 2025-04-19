#!/usr/bin/env python3
"""Slack bot that provides weather information using LangGraph and Anthropic Claude."""

import logging
import os
import requests
from typing import Annotated, TypedDict

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()
slack_app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

# Store conversation histories by thread for memory
thread_histories = {}

class State(TypedDict):
    """Represents the state passed between LangGraph nodes."""
    messages: Annotated[list, add_messages]
    slack_channel: str
    slack_thread_ts: str

def get_coordinates(city):
    """Get latitude and longitude for a city."""
    url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en&format=json"
    response = requests.get(url, timeout=10)
    data = response.json()
    
    if not data.get("results"):
        raise Exception(f"Could not find coordinates for city: {city}")
    
    result = data["results"][0]
    return result["latitude"], result["longitude"]

def get_weather(latitude, longitude):
    """Get weather data for coordinates."""
    url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code"
    response = requests.get(url, timeout=10)
    data = response.json()
    
    if "error" in data:
        raise Exception(f"Weather API error: {data['error']}")
    
    # Convert temperature from Celsius to Fahrenheit
    data["current"]["temperature_2m"] = data["current"]["temperature_2m"] * 9 / 5 + 32
    return data["current"]

def weather_code_to_description(code):
    """Convert weather code to human-readable description."""
    weather_codes = {
        0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
        45: "Fog", 48: "Depositing rime fog", 51: "Light drizzle",
        53: "Moderate drizzle", 55: "Dense drizzle", 61: "Slight rain",
        63: "Moderate rain", 65: "Heavy rain", 71: "Slight snow fall",
        73: "Moderate snow fall", 75: "Heavy snow fall", 77: "Snow grains",
        80: "Slight rain showers", 81: "Moderate rain showers",
        82: "Violent rain showers", 85: "Slight snow showers",
        86: "Heavy snow showers", 95: "Thunderstorm",
        96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail"
    }
    return weather_codes.get(code, "Unknown weather condition")

@tool
def weather_tool(city: str) -> str:
    """Get the weather for a given city."""
    try:
        latitude, longitude = get_coordinates(city)
        weather_data = get_weather(latitude, longitude)
        return (
            f"Weather for {city}:\n"
            f"Temperature: {weather_data['temperature_2m']:.1f}°F\n"
            f"Conditions: {weather_code_to_description(weather_data['weather_code'])}\n"
            f"Humidity: {weather_data['relative_humidity_2m']}%\n"
            f"Wind Speed: {weather_data['wind_speed_10m']} mph"
        )
    except Exception as e:
        logger.error(f"Error in weather_tool: {str(e)}")
        return f"Error fetching weather for {city}: {str(e)}"

def agent(state: State) -> State:
    """Process messages with the LLM and update thread history."""
    messages = state["messages"]
    thread_ts = state.get("slack_thread_ts")
    
    # Invoke LLM with full conversation history
    response = llm.invoke(messages)
    
    # Update thread history for future reference
    result_messages = messages + [response]
    thread_histories[thread_ts] = result_messages
    
    return {**state, "messages": result_messages}

def send_to_slack(state: State) -> State:
    """Send the agent's response to Slack."""
    channel = state.get("slack_channel")
    thread_ts = state.get("slack_thread_ts")

    slack_app.client.chat_postMessage(
        channel=channel, thread_ts=thread_ts, text=state["messages"][-1].content)
    
    return state

def should_continue(state: State) -> str:
    """Determine if we need to call a tool or send the response."""
    last_message = state["messages"][-1]
    if isinstance(last_message, AIMessage) and hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tool_node"
    return "send_to_slack"

# Initialize LLM with Anthropic Claude
llm = ChatAnthropic(
    model="claude-3-5-sonnet-20240620",
    api_key=os.environ.get("ANTHROPIC_API_KEY"),
    system="You are a helpful weather assistant that provides accurate weather information and suggests appropriate outdoor activities. Always use the weather_tool when users ask about weather conditions for specific locations in a short sentence."
).bind_tools([weather_tool])

# Configure the graph
tools = [weather_tool]
tool_node = ToolNode(tools)

workflow = StateGraph(State)
workflow.add_node("agent", agent)
workflow.add_node("tool_node", tool_node)
workflow.add_node("send_to_slack", send_to_slack)

workflow.set_entry_point("agent")
workflow.add_conditional_edges(
    "agent", should_continue, 
    {"tool_node": "tool_node", "send_to_slack": "send_to_slack"}
)
workflow.add_edge("tool_node", "agent")
workflow.add_edge("send_to_slack", END)

graph = workflow.compile()

# Print the ASCII representation of the graph
print("\nLangGraph Weather Agent Workflow:")
print(graph.get_graph().draw_ascii())

@slack_app.event("message")
def handle_message(body):
    """Process incoming Slack messages with conversation history."""
    event = body.get("event", {})
    text = event.get("text", "")
    channel = event.get("channel")
    thread_ts = event.get("thread_ts", event.get("ts"))
    
    messages = [HumanMessage(content=text)]
    
    # Add conversation history for thread continuations
    if thread_ts in thread_histories:
        messages = thread_histories[thread_ts] + messages
    
    initial_state = {
        "messages": messages,
        "slack_channel": channel,
        "slack_thread_ts": thread_ts,
    }
    
    graph.invoke(initial_state)

# Start the application
if __name__ == "__main__":
    handler = SocketModeHandler(slack_app, os.environ.get("SLACK_APP_TOKEN"))
    handler.start()
