FROM python:3.11-slim

RUN pip install --upgrade pip && \
    pip install --no-cache-dir --retries 5 --timeout 60 dbt-postgres==1.9.0

WORKDIR /dbt
COPY demo_project/ /dbt/demo_project/
COPY server.py /dbt/server.py

ENV DBT_PROJECT_DIR=/dbt/demo_project
ENV PORT=8001

EXPOSE 8001

CMD ["python", "server.py"]
