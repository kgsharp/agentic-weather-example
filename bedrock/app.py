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
    
    def __init__(self, agent_id: str, agent_alias_id: str) -> None:
        self.agent_id = agent_id
        self.agent_alias_id = agent_alias_id
        self.bedrock_agent = boto3.client('bedrock-agent-runtime')

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


def get_terraform_output(output_name: str) -> Optional[str]:
    """Get Terraform output value."""
    try:
        infra_dir = os.path.join(os.path.dirname(__file__), 'infra')
        result = subprocess.run(
            ['terraform', 'output', '-raw', output_name],
            cwd=infra_dir, check=True, 
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logger.error(f"Terraform error: {e.stderr}")
        return None


@slack_app.event("message")
def handle_message(body: Dict[str, Any]) -> None:
    """Handle Slack messages by invoking the weather agent."""
    event = body.get("event", {})
    text = event.get("text", "")
    channel = event.get("channel")
    thread_ts = event.get("thread_ts", event.get("ts"))
    session_id = f"{channel}-{thread_ts}"  # Per-thread agent memory
    
    agent_id = get_terraform_output('bedrock_agent_id')
    agent_alias_id = get_terraform_output('weather_assistant_alias_id')
    
    if agent_id and agent_alias_id:
        response = WeatherAgent(agent_id, agent_alias_id).get_weather(text, session_id)
        slack_app.client.chat_postMessage(channel=channel, thread_ts=thread_ts, text=response)
    else:
        logger.error("Failed to get agent ID or alias ID from Terraform")


if __name__ == "__main__":
    SocketModeHandler(slack_app, os.environ.get("SLACK_APP_TOKEN")).start()
