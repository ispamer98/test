FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    OBRASEC_DATA=/datos \
    OBRASEC_PUBLIC=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY run.py arranque.py ./

# Los datos viven en un volumen: actualizar la imagen nunca borra una obra.
VOLUME ["/datos"]
EXPOSE 8321

# Sin root: si alguien encuentra un fallo en la app, no encuentra el servidor.
RUN useradd --create-home --uid 10001 obrasec && mkdir -p /datos && chown -R obrasec /datos /app
USER obrasec

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8321/api/estado', timeout=4).status==200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8321", \
     "--proxy-headers", "--forwarded-allow-ips", "*"]
