terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}
data "aws_region" "current" {}

locals {
  account_id = data.aws_caller_identity.current.account_id
  partition  = data.aws_partition.current.partition
  region     = data.aws_region.current.name
}

# IAM role for the Bedrock agent
resource "aws_iam_role" "bedrock_agent_role" {
  name_prefix = "AmazonBedrockExecutionRoleForAgents_"
  assume_role_policy = jsonencode({
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "bedrock.amazonaws.com" }
      Condition = {
        StringEquals = { "aws:SourceAccount" = local.account_id }
        ArnLike      = { "AWS:SourceArn" = "arn:${local.partition}:bedrock:${local.region}:${local.account_id}:agent/*" }
      }
    }]
    Version = "2012-10-17"
  })
}

# Policy for the Bedrock agent
resource "aws_iam_role_policy" "bedrock_agent_policy" {
  name = "BedrockAgentPolicy"
  role = aws_iam_role.bedrock_agent_role.id
  policy = jsonencode({
    Statement = [{
      Action = ["bedrock:InvokeModel", "lambda:InvokeFunction"]
      Effect = "Allow"
      Resource = [
        "arn:${local.partition}:bedrock:${local.region}::foundation-model/anthropic.claude-v2",
        aws_lambda_function.get_weather.arn
      ]
    }]
    Version = "2012-10-17"
  })
}

resource "aws_iam_role_policy_attachment" "bedrock_full_access" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonBedrockFullAccess"
  role       = aws_iam_role.bedrock_agent_role.name
}

# Lambda execution role
resource "aws_iam_role" "lambda_execution_role" {
  name_prefix = "LambdaExecutionRole_"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  role       = aws_iam_role.lambda_execution_role.name
}

# ECR repository for the Lambda
resource "aws_ecr_repository" "weather_lambda" {
  name = "weather-lambda"
}

# Lambda function using container image
resource "aws_lambda_function" "get_weather" {
  function_name = "get-weather-data"
  role          = aws_iam_role.lambda_execution_role.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.weather_lambda.repository_url}:latest"
  timeout       = 30
  memory_size   = 128
  architectures = ["arm64"]
}

resource "aws_lambda_permission" "allow_bedrock_invoke" {
  statement_id    = "AllowBedrockInvoke"
  action          = "lambda:InvokeFunction"
  function_name   = aws_lambda_function.get_weather.function_name
  principal       = "bedrock.amazonaws.com"
  source_account  = local.account_id
  source_arn      = "arn:${local.partition}:bedrock:${local.region}:${local.account_id}:agent/*"
}

# Bedrock agent
resource "aws_bedrockagent_agent" "weather_assistant" {
  agent_name              = "weather-assistant"
  agent_resource_role_arn = aws_iam_role.bedrock_agent_role.arn
  instruction             = "You are a weather assistant who can answer weather questions in a given location. Do not make up information. Do not answer questions about anything unrelated to weather reports. Do not offer to do anything else than weather questions. When you determine the forecast, suggest a fun activity to do outside based on the weather conditions."
  foundation_model        = "anthropic.claude-3-5-sonnet-20240620-v1:0"
  idle_session_ttl_in_seconds = 300
  memory_configuration {
    enabled_memory_types = ["SESSION_SUMMARY"]
    storage_days = 1
  }
}

resource "null_resource" "wait_for_agent" {
  provisioner "local-exec" { command = "sleep 15" }
  depends_on = [aws_bedrockagent_agent.weather_assistant]
}

resource "aws_bedrockagent_agent_alias" "weather_assistant_alias" {
  agent_alias_name = "weather-assistant-alias"
  agent_id         = aws_bedrockagent_agent.weather_assistant.id
  description      = "Alias for the weather assistant agent"
}

resource "aws_bedrockagent_agent_action_group" "weather_action_group" {
  action_group_name          = "get-weather-from-lambda"
  agent_id                   = aws_bedrockagent_agent.weather_assistant.id
  agent_version              = "DRAFT"
  skip_resource_in_use_check = true
  
  action_group_executor {
    lambda = aws_lambda_function.get_weather.arn
  }
  
  function_schema {
    member_functions {
      functions {
        name        = "get-weather-data"
        description = "Get weather data for a specific location"
        parameters {
          map_block_key = "location"
          type          = "string"
          description   = "The name of the city to get weather information for"
          required      = true
        }
        parameters {
          map_block_key = "intent"
          type          = "string"
          description   = "The intent of the request, should be 'get_weather'"
          required      = true
        }
      }
    }
  }
  
  depends_on = [null_resource.wait_for_agent]
}

output "bedrock_agent_id" {
  value       = aws_bedrockagent_agent.weather_assistant.id
  description = "The ID of the Bedrock agent."
}

output "weather_assistant_alias_id" {
  value = aws_bedrockagent_agent_alias.weather_assistant_alias.agent_alias_id
}