FROM python:3.12.3-slim-bookworm

WORKDIR /app

RUN pip install --upgrade pip

RUN pip install --only-binary=:all: pydantic-core==2.16.3

COPY requirements.txt .
RUN pip install --only-binary=:all: -r requirements.txt

COPY . .

RUN ls -la /app/assets/ && echo "Assets verified"

RUN chmod +x /app/start.sh

EXPOSE 8000

CMD ["/bin/sh", "/app/start.sh"]
