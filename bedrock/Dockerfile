FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY weather_lambda.py .
CMD ["python3", "-m", "awslambdaric", "weather_lambda.lambda_handler"]