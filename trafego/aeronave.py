import uuid

from trafego.regras import (
    AGING_INTERVALO_MIN,
    PRIORIDADE_MINIMA_AGING,
    PRIORIDADES,
)


class Aeronave:
    def __init__(self, codigo, origem, destino, motivo, relogio):
        if motivo not in PRIORIDADES:
            raise ValueError(f"Motivo desconhecido: {motivo}")
        if not codigo or not codigo.strip():
            raise ValueError("O código do voo é obrigatório.")

        self._id = str(uuid.uuid4())
        self._codigo = codigo.strip().upper()
        self._origem = origem.strip().upper()
        self._destino = destino.strip().upper()
        self._motivo = motivo
        self._prioridade_base = PRIORIDADES[motivo]
        self._relogio = relogio
        self._criada_em = relogio.agora()
        self._status = "AGUARDANDO"
        self._pousou_em = None
        self._prioridade_registrada = self._prioridade_base

    @property
    def id(self):
        return self._id

    @property
    def codigo(self):
        return self._codigo

    @property
    def origem(self):
        return self._origem

    @property
    def destino(self):
        return self._destino

    @property
    def motivo(self):
        return self._motivo

    @property
    def prioridade_base(self):
        return self._prioridade_base

    @property
    def criada_em(self):
        return self._criada_em

    @property
    def status(self):
        return self._status

    @property
    def pousou_em(self):
        return self._pousou_em

    def tempo_espera(self):
        fim = self._pousou_em if self._pousou_em is not None else self._relogio.agora()
        return fim - self._criada_em

    def prioridade_atual(self):
        if self._prioridade_base <= PRIORIDADE_MINIMA_AGING:
            return self._prioridade_base
        bonus = int(self.tempo_espera() // AGING_INTERVALO_MIN)
        return max(PRIORIDADE_MINIMA_AGING, self._prioridade_base - bonus)

    def marcar_pousada(self):
        self._status = "POUSOU"
        self._pousou_em = self._relogio.agora()

    def marcar_removida(self):
        self._status = "REMOVIDA"

    def __repr__(self):
        return f"Aeronave({self._codigo}, P{self.prioridade_atual()}, {self._status})"
