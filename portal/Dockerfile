FROM python:3.11-slim
WORKDIR /app
COPY portal/requirements.txt ./portal/requirements.txt
RUN pip install --no-cache-dir -r portal/requirements.txt
COPY portal/app.py portal/app.py
COPY portal/templates ./portal/templates
COPY orchestrator/ ./orchestrator/
COPY collector/ ./collector/
COPY config/ ./config/
ENV TARGET_URL=http://target:8099
ENV OPENAEV_URL=http://host.docker.internal:8888
EXPOSE 8500
CMD ["python", "portal/app.py"]
