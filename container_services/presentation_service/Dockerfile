FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
#RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --upgrade pip && \
    pip install --no-cache-dir cryptography>=3.0.0 && \
    pip install --no-cache-dir -r requirements.txt
COPY app.py .
COPY templates ./templates
CMD ["python", "app.py"]