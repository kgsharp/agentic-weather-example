#!/usr/bin/env python3
"""AWS Bedrock Weather Agent integration with Slack."""

import os
import logging
import subprocess
from typing import Dict, Any, Optional

import boto3
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

slack_app = App(token=os.environ.get("SLACK_BOT_TOKEN"))


class WeatherAgent:
    """AWS Bedrock weather agent handler."""
    def __init__(self) -> None:
        self.bedrock_agent = boto3.client('bedrock-agent-runtime')
        infra_dir = os.path.join(os.path.dirname(__file__), 'infra')

        self.agent_id = subprocess.run(
            ['terraform', 'output', '-raw', 'bedrock_agent_id'],
            cwd=infra_dir, check=True, 
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        ).stdout.strip()
        
        self.agent_alias_id = subprocess.run(
            ['terraform', 'output', '-raw', 'weather_assistant_alias_id'],
            cwd=infra_dir, check=True, 
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        ).stdout.strip()
            
        logger.info(f"Initializing WeatherAgent with agent_id={self.agent_alias_id}")

    def get_weather(self, input_text: str, session_id: str = 'weather-session') -> str:
        """Get weather for a location via Bedrock agent."""
        try:
            response = self.bedrock_agent.invoke_agent(
                agentId=self.agent_id,
                agentAliasId=self.agent_alias_id,
                sessionId=session_id,
                inputText=input_text
            )
            
            output = ""
            for event in response['completion']:
                if 'chunk' in event:
                    output += event['chunk']['bytes'].decode('utf-8')
            return output
        except Exception as e:
            logger.error(f"Error invoking agent: {e}")
            return f"Error getting weather: {str(e)}"


@slack_app.event("message")
def handle_message(body: Dict[str, Any]) -> None:
    """Handle Slack messages by invoking the weather agent."""
    agent = slack_app.agent
    
    event = body.get("event", {})
    text = event.get("text", "")
    channel = event.get("channel")
    thread_ts = event.get("thread_ts", event.get("ts"))
    session_id = f"{channel}-{thread_ts}"  # Per-thread agent memory
    
    response = agent.get_weather(text, session_id)
    slack_app.client.chat_postMessage(channel=channel, thread_ts=thread_ts, text=response)


if __name__ == "__main__":
    weather_agent = WeatherAgent()
    slack_app.agent = weather_agent
    
    logger.info("Starting Slack handler")
    SocketModeHandler(slack_app, os.environ.get("SLACK_APP_TOKEN")).start()
