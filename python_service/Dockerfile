FROM python:3.10-slim
WORKDIR /app
ENV DEBIAN_FRONTEND=noninteractive

# minimal runtime deps (PIL needs libjpeg)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg-dev zlib1g-dev libpng-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
EXPOSE 8000
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]
