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
        self._conexao = sqlite3.connect(self._caminho, check_same_thread=False)
        self._conexao.execute(

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

    def limpar_logs(self):
        self._conexao.execute("DELETE FROM logs")
        self._conexao.commit()
