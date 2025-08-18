FROM python:3.11-slim
WORKDIR /app
COPY libs /app/libs
# Install shared libs package
RUN pip install --no-cache-dir /app/libs
COPY containers/collector-scheduler/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY containers/collector-scheduler/ /app
CMD ["python", "main.py"]
