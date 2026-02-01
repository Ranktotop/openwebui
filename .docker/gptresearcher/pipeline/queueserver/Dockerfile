FROM python:3.12-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY .docker/gptresearcher/pipeline/queueserver/src/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY .docker/gptresearcher/pipeline/queueserver/src/service.py .

# Expose port
EXPOSE 8001
ARG VERSION
ENV VERSION=${VERSION}

# Run the server
CMD ["uvicorn", "service:app", "--host", "0.0.0.0", "--port", "8001", "--log-level", "info"]