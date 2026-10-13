"""Configuração por variáveis de ambiente: leitura do .env local e nomes das variáveis por cliente."""

from __future__ import annotations

import os
from pathlib import Path


def var_cliente(prefixo: str, cliente_id: str) -> str:
    """KOMMO_TOKEN_ + 'imob-a' → KOMMO_TOKEN_IMOB_A (o cliente_id é o nome da pasta do cliente)."""
    return prefixo + cliente_id.upper().replace("-", "_")


def carregar_env(caminho: str | os.PathLike = ".env") -> list[str]:
    """Lê um arquivo KEY=valor para o ambiente, sem sobrescrever o que já está definido.

    O que vem do ambiente (Docker, n8n, terminal) sempre vence o arquivo. Comentários (`# …`) no fim
    da linha e aspas em volta do valor são removidos; chave vazia é ignorada. Devolve as chaves lidas.
    """
    p = Path(caminho)
    if not p.is_file():
        return []
    lidas = []
    for linha in p.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        chave = chave.strip().removeprefix("export ").strip()
        valor = valor.strip()
        if valor[:1] in "\"'" and valor[-1:] == valor[:1] and len(valor) > 1:
            valor = valor[1:-1]
        else:
            valor = valor.split(" #", 1)[0].split("\t#", 1)[0].strip()
            if valor.startswith("#"):
                valor = ""
        if chave and valor and chave not in os.environ:
            os.environ[chave] = valor
            lidas.append(chave)
    return lidas
