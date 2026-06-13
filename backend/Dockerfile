FROM python:3.12.3-slim-bookworm

WORKDIR /app

RUN pip install --upgrade pip

# Install pydantic-core from pre-built wheel first, explicitly
RUN pip install --only-binary=:all: pydantic-core==2.16.3

COPY requirements.txt .
RUN pip install --only-binary=:all: -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
