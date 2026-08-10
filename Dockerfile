FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ .

#ENV COOKIES=/app/cookies.txt
#COPY cookies.txt /app/cookies.txt

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8089"]
