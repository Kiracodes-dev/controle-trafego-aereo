"""Classe Aeronave: representa cada voo cadastrado no simulador."""

import uuid

from trafego.regras import (
    AGING_INTERVALO_MIN,
    PRIORIDADE_MINIMA_AGING,
    PRIORIDADES,
)


class Aeronave:
    """Representa uma aeronave aguardando autorização de pouso."""

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
        # Guarda a última prioridade já registrada no log, para o aging
        # gerar um registro só quando a prioridade realmente muda
        self._prioridade_registrada = self._prioridade_base

    @classmethod
    def restaurar(cls, dados, relogio):
        """Recria uma aeronave a partir de um registro salvo no banco."""
        aeronave = cls(dados["codigo"], dados["origem"], dados["destino"], dados["motivo"], relogio)
        aeronave._id = dados["id"]
        aeronave._criada_em = dados["criada_em"]
        aeronave._status = dados["status"]
        aeronave._pousou_em = dados["pousou_em"]
        aeronave._prioridade_registrada = dados["prioridade_registrada"]
        return aeronave

    def para_dict(self):
        """Converte a aeronave em dicionário para salvar no banco."""
        return {
            "id": self._id,
            "codigo": self._codigo,
            "origem": self._origem,
            "destino": self._destino,
            "motivo": self._motivo,
            "prioridade_base": self._prioridade_base,
            "prioridade_registrada": self._prioridade_registrada,
            "criada_em": self._criada_em,
            "status": self._status,
            "pousou_em": self._pousou_em,
        }

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
        """Minutos transcorridos desde o cadastro (ou até o pouso)."""
        fim = self._pousou_em if self._pousou_em is not None else self._relogio.agora()
        return fim - self._criada_em

    def prioridade_atual(self):
        """Prioridade com aging: a cada AGING_INTERVALO_MIN minutos melhora 1 nível,
        até o limite PRIORIDADE_MINIMA_AGING. Emergências (1) não mudam."""
        if self._prioridade_base <= PRIORIDADE_MINIMA_AGING:
            return self._prioridade_base
        bonus = int(self.tempo_espera() // AGING_INTERVALO_MIN)
        return max(PRIORIDADE_MINIMA_AGING, self._prioridade_base - bonus)

    def atualizar_prioridade_registrada(self):
        """Retorna (anterior, atual) se o aging mudou a prioridade; senão None."""
        atual = self.prioridade_atual()
        if atual == self._prioridade_registrada:
            return None
        anterior = self._prioridade_registrada
        self._prioridade_registrada = atual
        return anterior, atual

    def marcar_pousada(self):
        self._status = "POUSOU"
        self._pousou_em = self._relogio.agora()

    def marcar_removida(self):
        self._status = "REMOVIDA"

    def __repr__(self):
        return f"Aeronave({self._codigo}, P{self.prioridade_atual()}, {self._status})"
