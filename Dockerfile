# 1. Escolhemos a imagem base (Python leve)
FROM python:3.11-slim

# 2. Definimos onde os arquivos ficarão dentro do contêiner
WORKDIR /app

# 3. Instalamos as dependências do sistema necessárias para o SimpleKML/HTTPX
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 4. Copiamos o arquivo de requisitos e instalamos
# (Crie um arquivo requirements.txt com: fastapi, uvicorn, httpx, python-dotenv, simplekml)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copiamos o restante do código do projeto
COPY . .

# 6. Expomos a porta que o FastAPI vai usar
EXPOSE 8000

# 7. Comando para rodar a aplicação
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]