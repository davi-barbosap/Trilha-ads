FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml ./
COPY trilha ./trilha
COPY playbooks ./playbooks
# /logs nasce com dono trilha: um volume montado ali herda o dono, e o registro de envios não falha por permissão
RUN pip install --no-cache-dir . && useradd --create-home trilha && mkdir -p /logs && chown trilha /logs
USER trilha
ENV TRILHA_CLIENTES_DIR=/clientes TRILHA_PLAYBOOKS_DIR=/app/playbooks TRILHA_SIMULAR=1 TRILHA_LOG_DIR=/logs
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request;urllib.request.urlopen('http://localhost:8080/saude')"
CMD ["python", "-m", "trilha", "servir", "--porta", "8080"]
