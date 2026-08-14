FROM python:3.11-slim
WORKDIR /app
COPY consumer/requirements.txt consumer/requirements.txt
RUN pip install --no-cache-dir -r consumer/requirements.txt
COPY shared/ shared/
COPY consumer/ consumer/
COPY ml/model.joblib ml/model.joblib
CMD ["python", "-m", "consumer.main"]
