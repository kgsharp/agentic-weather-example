FROM node:18-alpine

RUN apk add --update graphicsmagick tzdata
WORKDIR /app
COPY Get_Weather_Agent.json Get_Weather_Agent.json
RUN npm install -g n8n@latest
RUN n8n import:workflow --input Get_Weather_Agent.json
RUN n8n update:workflow --all --active=true

ENV NODE_ENV=production
ENV N8N_PORT=8080
ENV WEBHOOK_URL=http://localhost:8080/
ENV GENERIC_TIMEZONE=UTC
ENV N8N_USER_MANAGEMENT_DISABLED=false

EXPOSE 8080

CMD ["n8n", "start"] 