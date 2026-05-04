FROM python:3.11-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1
# system deps for lxml
RUN apt-get update && apt-get install -y \
	gcc libxml2-dev libxslt1-dev libpq-dev build-essential \
	curl ca-certificates wget unzip tar && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
# Install python requirements
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
COPY .env.example .env
# Create data dir
RUN mkdir -p /app/data

# Default command runs uvicorn serving FastAPI; worker can be run directly as module
CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]
