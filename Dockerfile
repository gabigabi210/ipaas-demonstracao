FROM python:3.12-slim
WORKDIR /app
COPY . .
ENV PYTHONUNBUFFERED=1
# O comando de cada serviço é definido no docker-compose.yml
CMD ["python", "-m", "ipaas.server"]
