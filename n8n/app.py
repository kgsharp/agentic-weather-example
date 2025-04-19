#!/usr/bin/env python3
"""
This is a simple Slack app that sends messages to n8n as a webhook since n8n doesn't support socket mode.
"""

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import logging
import os
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

slack_app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

N8N_WEBHOOK_URL = "http://localhost:8080/webhook/6216d667-5564-454c-9947-bc27ba3de28e"

@slack_app.event("message")
def handle_message(body):
    """Send slack messages to n8n."""
    event = body.get("event", {})
    text = event.get("text", "")
    channel = event.get("channel")
    thread_ts = event.get("thread_ts", event.get("ts"))
    #send message to n8n via post request
    requests.post(N8N_WEBHOOK_URL, json={"text": text, "channel": channel, "thread_ts": thread_ts})

if __name__ == "__main__":
    SocketModeHandler(slack_app, os.environ.get("SLACK_APP_TOKEN")).start()
