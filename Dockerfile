FROM node:20-bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-venv python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

ENV PATH="/opt/venv/bin:$PATH"
RUN python3 -m venv /opt/venv \
    && pip install --no-cache-dir -r api/requirements.txt

WORKDIR /app/web
RUN npm ci && npm run build

WORKDIR /app
ENV API_URL=http://127.0.0.1:8000 NODE_ENV=production

CMD ["bash","-c","(cd /app/api && uvicorn main:app --host 127.0.0.1 --port 8000) & cd /app/web && exec npm run start -- -p ${PORT:-3000}"]
