FROM python:3.12-slim
RUN useradd --system --uid 10001 appuser
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app app
COPY scenarios scenarios
COPY scripts scripts
RUN mkdir -p /app/artifacts && chown -R appuser:appuser /app
USER 10001
EXPOSE 8000
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]
