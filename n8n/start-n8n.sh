#!/bin/bash
docker build -t n8n-local .
docker run -d \
  -p 8080:8080 \
  -v ~/.n8n:/home/node/.n8n \
  --restart unless-stopped \
  n8n-local

echo "n8n is now running in the background. Go to http://localhost:8080 to access the web interface."
