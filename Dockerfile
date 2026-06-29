FROM python:3.12-slim

# Directorio de trabajo
WORKDIR /app

# Instalamos las librerías de Python directamente
# Subimos el timeout por si tu internet está lento
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiamos el resto de tus archivos
COPY . .

# Exponemos el puerto
EXPOSE 8501

# Comando directo al módulo de streamlit
ENTRYPOINT ["python", "-m", "streamlit", "run", "ingest.py", "--server.port=8501", "--server.address=0.0.0.0"]