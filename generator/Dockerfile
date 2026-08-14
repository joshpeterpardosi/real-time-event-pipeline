FROM python:3.11-slim
WORKDIR /app
COPY generator/requirements.txt generator/requirements.txt
RUN pip install --no-cache-dir -r generator/requirements.txt
COPY shared/ shared/
COPY generator/ generator/
ENTRYPOINT ["python", "-m", "generator.main"]
