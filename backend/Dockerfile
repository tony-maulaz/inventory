FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV POETRY_VIRTUALENVS_CREATE=false
ENV POETRY_NO_INTERACTION=1

WORKDIR /code

RUN pip install --no-cache-dir poetry

COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root

# Trust HEIG internal CAs (for LDAP) baked into the image
RUN mkdir -p /usr/local/share/ca-certificates/extra
COPY HEIG-RootCA.crt HEIG-SCA01.crt /usr/local/share/ca-certificates/extra/
RUN update-ca-certificates

# App source
COPY app ./app
COPY init_db.py .
COPY alembic.ini .
COPY alembic ./alembic
COPY ldap_debug.py .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
