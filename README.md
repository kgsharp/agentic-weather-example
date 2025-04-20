# Agentic Weather Examples

This repository demonstrates three different approaches to building AI-powered weather agents that integrate with Slack.

## Overview

All three examples connect to:
1. A Slack bot interface for user interaction.
2. A free weather API (OpenWeather or Open-Meteo) for data as a "tool".
3. An AI model (Anthropic's Claude Sonnnet 3.5) for natural language understanding - n8n and langchain use the direct API while Bedrock uses it as one of its supported foundational models.
4. Include basic memory examples so that bot can have context along a single slack thread.
5. Responds in Slack to give you weather and tips on what you can do that day.

## Implementation Examples

### 1. LangChain/LangGraph Weather Agent

**Directory:** `langchain/`

This implementation uses LangChain/LangGraph to create a simple yet powerful agent with conversation memory.

**Key Components and Features:**
- LangGraph for creating a multi-step workflow
- LangChain for LLM integration
- Tool-calling pattern to get weather information
- Suggests activities based on weather conditions

### 2. AWS Bedrock Weather Agent

**Directory:** `bedrock/`

This implementation leverages AWS Bedrock to create a serverless agent with AWS-managed components.

**Key Components and Features:**
- AWS Bedrock Agent for natural language understanding
- AWS Lambda for executing weather API calls (the "action group")
- Terraform for infrastructure-as-code deployment
- Fully Serverless architecture
- Containerized Lambda function (only runs as needed)
- Fully AWS-managed components and IAM permissions

### 3. n8n Workflow Weather Agent

**Directory:** `n8n/`

This implementation uses n8n, a workflow automation platform, to orchestrate the weather agent functionality.

**Key Components and Features:**
- n8n for workflow orchestration using their AI Agent node
- a separate slack connector to use to send requests to n8n server
- Visual workflow editor is available
- No-code/low-code approach
- Webhook integration for events

## Getting Started (Setup)

- Set up Slack

You need a slack bot created and added to a chat room. This is supported on the free version of slack.

1. Create a new Slack app using the provided manifest in `slack/slack-manifest.json`
2. Install the app to your workspace
3. Create an app token with `connections:write` permissions
4. Set the slack environment variables:
   ```
   export SLACK_BOT_TOKEN=xoxb-your-token
   export SLACK_APP_TOKEN=xapp-your-token
   ```

- Set the Anthropic API Key

You can get this from https://www.anthropic.com/api. It is only $5 to get a key (not required for the AWS Bedrock Example)

   ```
   export ANTHROPIC_API_KEY=sk-ant-your-key
   ```

- You will need Docker installed
- You will need Python (3.12 is fine)
- For AWS Bedrock Example, you will need access to an AWS account with credentials that has permissions to create bedrock agents and update IAM perms
- For AWS Bedrock Example, you will need Terraform installed

There is a README under each example for more details on that particular setup.

## License

This project is released under The Unlicense. See the LICENSE file for details.