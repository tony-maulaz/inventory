FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV POETRY_VIRTUALENVS_CREATE=false
ENV POETRY_NO_INTERACTION=1

WORKDIR /code

RUN pip install --no-cache-dir poetry

COPY backend/pyproject.toml backend/poetry.lock ./
RUN poetry install --no-root

# Trust HEIG internal CAs (for LDAP) baked into the image
RUN mkdir -p /usr/local/share/ca-certificates/extra
COPY HEIG-RootCA.crt HEIG-SCA01.crt /usr/local/share/ca-certificates/extra/
RUN update-ca-certificates

# App source
COPY backend/app ./app
COPY backend/init_db.py .
COPY backend/alembic.ini .
COPY backend/alembic ./alembic
COPY backend/ldap_debug.py .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
