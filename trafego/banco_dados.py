"""Classe BancoDeDados (SQLite) e entidade LogAuditoria."""

import sqlite3
from dataclasses import dataclass
from datetime import datetime


@dataclass
class LogAuditoria:
    id: int
    timestamp: str
    evento: str
    codigo_voo: str
    detalhes: str


class BancoDeDados:
    def __init__(self, caminho="trafego_aereo.db"):
        self._caminho = caminho
        self._conexao = None
        self.conectar_banco()

    def conectar_banco(self):
        """Cria o banco e as tabelas, caso não existam."""
        # check_same_thread=False: o Streamlit pode acessar o banco por threads diferentes
        self._conexao = sqlite3.connect(self._caminho, check_same_thread=False)
        self._conexao.row_factory = sqlite3.Row
        self._conexao.executescript(
            """
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                evento TEXT NOT NULL,
                codigo_voo TEXT,
                detalhes TEXT
            );
            CREATE TABLE IF NOT EXISTS aeronaves (
                id TEXT PRIMARY KEY,
                codigo TEXT NOT NULL,
                origem TEXT,
                destino TEXT,
                motivo TEXT NOT NULL,
                prioridade_base INTEGER NOT NULL,
                prioridade_registrada INTEGER NOT NULL,
                criada_em REAL NOT NULL,
                status TEXT NOT NULL,
                pousou_em REAL
            );
            -- Guarda valores soltos da simulação, como o minuto atual do relógio
            CREATE TABLE IF NOT EXISTS estado (
                chave TEXT PRIMARY KEY,
                valor REAL
            );
            """
        )
        self._conexao.commit()

    def registrar_log(self, evento, codigo_voo, detalhes):
        self._conexao.execute(
            "INSERT INTO logs (timestamp, evento, codigo_voo, detalhes) VALUES (?, ?, ?, ?)",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), evento, codigo_voo, detalhes),
        )
        self._conexao.commit()

    def listar_logs(self, limite=500):
        cursor = self._conexao.execute(
            "SELECT id, timestamp, evento, codigo_voo, detalhes FROM logs "
            "ORDER BY id DESC LIMIT ?",
            (limite,),
        )
        return [LogAuditoria(*linha) for linha in cursor.fetchall()]

    def salvar_aeronave(self, dados):
        # INSERT OR REPLACE: insere uma aeronave nova ou atualiza uma que já existe
        self._conexao.execute(
            "INSERT OR REPLACE INTO aeronaves (id, codigo, origem, destino, motivo, prioridade_base, "
            "prioridade_registrada, criada_em, status, pousou_em) VALUES "
            "(:id, :codigo, :origem, :destino, :motivo, :prioridade_base, "
            ":prioridade_registrada, :criada_em, :status, :pousou_em)",
            dados,
        )
        self._conexao.commit()

    def carregar_aeronaves(self):
        cursor = self._conexao.execute("SELECT * FROM aeronaves ORDER BY criada_em")
        return [dict(linha) for linha in cursor.fetchall()]

    def salvar_relogio(self, minuto):
        self._conexao.execute(
            "INSERT OR REPLACE INTO estado (chave, valor) VALUES ('relogio', ?)", (minuto,)
        )
        self._conexao.commit()

    def carregar_relogio(self):
        linha = self._conexao.execute("SELECT valor FROM estado WHERE chave = 'relogio'").fetchone()
        return linha["valor"] if linha else 0.0

    def reiniciar(self):
        """Apaga aeronaves, relógio e logs para começar uma simulação do zero."""
        self._conexao.executescript("DELETE FROM aeronaves; DELETE FROM estado; DELETE FROM logs;")
        self._conexao.commit()
