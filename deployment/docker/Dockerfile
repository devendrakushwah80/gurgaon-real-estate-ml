FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements ./requirements
RUN pip install --no-cache-dir -r requirements/api.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.api:api", "--host", "0.0.0.0", "--port", "8000"]

