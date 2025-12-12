FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8084

CMD ["gunicorn", "app:create_app()", "--bind", "0.0.0.0:8084", "--workers", "2"]
