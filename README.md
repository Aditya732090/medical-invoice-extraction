# medical-invoice-extraction
A complete invoice data extraction pipeline using FastAPI, Java Spring Boot, Docker, and vision-capable LLMs. Automatically processes medical invoices (PDF/images), parses line items, totals, and metadata, and returns clean JSON outputs for downstream systems.
# Bajaj Invoice Extractor
This repository contains two services:
- **python_service**: FastAPI microservice that implements image preprocessing,
OCR (Tesseract), and a simple rule-based line-item extraction.

- **java_api**: Spring Boot app that accepts a file upload and forwards it to
the Python service, returning the JSON result.
## Quick start with Docker Compose
1. Build and start both services:
```bash
docker-compose up --bui