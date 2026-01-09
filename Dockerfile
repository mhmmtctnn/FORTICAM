FROM python:3.9-slim

WORKDIR /app

# Gerekli dosyaları kopyala
COPY requirements.txt .
COPY src/ ./src/

# Bağımlılıkları yükle
RUN pip install --no-cache-dir -r requirements.txt

# Streamlit portunu dışa aç
EXPOSE 8501

# Uygulamayı başlat
CMD ["streamlit", "run", "src/app.py", "--server.address=0.0.0.0"]
