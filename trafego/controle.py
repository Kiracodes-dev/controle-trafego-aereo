import random

from trafego.aeronave import Aeronave
from trafego.fila_prioridade import FilaDePrioridade
from trafego.regras import PRIORIDADES, SLA_MINUTOS, TEMPO_POUSO_MIN
from trafego.relogio import RelogioSimulado


class ControleTrafegoAereo:
    def __init__(self, banco, relogio=None):
        self._aeronaves = []
        self._banco = banco
        self._relogio = relogio or RelogioSimulado()

    @property
    def aeronaves(self):
        return list(self._aeronaves)

    @property
    def relogio(self):
        return self._relogio

    def cadastrar_aeronave(self, codigo, origem, destino, motivo):
        aeronave = Aeronave(codigo, origem, destino, motivo, self._relogio)
        self._aeronaves.append(aeronave)
        self._banco.registrar_log(
            "CADASTRO",
            aeronave.codigo,
            f"{aeronave.origem}->{aeronave.destino} | {motivo} | prioridade {aeronave.prioridade_base}",
        )
        return aeronave

    def construir_fila(self):
        fila = FilaDePrioridade()
        for aeronave in self._aeronaves:
            if aeronave.status != "AGUARDANDO":
                continue
            self._registrar_mudanca_prioridade(aeronave)
            fila.inserir(aeronave)
        return fila

    def processar_pouso(self):
        proxima = self.construir_fila().remover_proxima()
        if proxima is None:
            return None
        proxima.marcar_pousada()
        sla = SLA_MINUTOS[proxima.prioridade_base]
        situacao = "dentro do SLA" if proxima.tempo_espera() <= sla else "SLA VIOLADO"
        self._banco.registrar_log(
            "POUSO_AUTORIZADO",
            proxima.codigo,
            f"esperou {proxima.tempo_espera():.1f} min (SLA {sla} min) - {situacao}",
        )
        self.avancar_tempo(TEMPO_POUSO_MIN)
        return proxima

    def remover_aeronaves_aguardando(self):
        removidas = 0
        for aeronave in self._aeronaves:
            if aeronave.status == "AGUARDANDO":
                aeronave.marcar_removida()
                removidas += 1
        self._banco.registrar_log("REMOCAO", "-", f"{removidas} aeronave(s) removida(s) da fila")
        return removidas

    def avancar_tempo(self, minutos):
        self._relogio.avancar(minutos)
        self.construir_fila()

    def _registrar_mudanca_prioridade(self, aeronave):
        atual = aeronave.prioridade_atual()
        if atual != aeronave._prioridade_registrada:
            self._banco.registrar_log(
                "ALTERACAO_PRIORIDADE",
                aeronave.codigo,
                f"aging: prioridade {aeronave._prioridade_registrada} -> {atual} "
                f"após {aeronave.tempo_espera():.1f} min de espera",
            )
            aeronave._prioridade_registrada = atual

    def metricas(self):
        aguardando = [a for a in self._aeronaves if a.status == "AGUARDANDO"]
        pousadas = [a for a in self._aeronaves if a.status == "POUSOU"]
        esperas = [a.tempo_espera() for a in aguardando]
        atendimentos = [a.tempo_espera() for a in pousadas]
        dentro_sla = [a for a in pousadas if a.tempo_espera() <= SLA_MINUTOS[a.prioridade_base]]
        estourando = [a for a in aguardando if a.tempo_espera() > SLA_MINUTOS[a.prioridade_base]]
        return {
            "aguardando": len(aguardando),
            "pousadas": len(pousadas),
            "espera_media": sum(esperas) / len(esperas) if esperas else 0.0,
            "espera_maxima": max(esperas) if esperas else 0.0,
            "atendimento_medio": sum(atendimentos) / len(atendimentos) if atendimentos else 0.0,
            "sla_cumprido_pct": 100 * len(dentro_sla) / len(pousadas) if pousadas else 100.0,
            "aguardando_fora_sla": len(estourando),
        }

    def sla_por_prioridade(self):
        resultado = []
        for nivel, limite in SLA_MINUTOS.items():
            pousadas = [a for a in self._aeronaves if a.status == "POUSOU" and a.prioridade_base == nivel]
            ok = [a for a in pousadas if a.tempo_espera() <= limite]
            resultado.append({
                "prioridade": nivel,
                "sla_min": limite,
                "pousos": len(pousadas),
                "dentro_sla": len(ok),
                "cumprimento_pct": round(100 * len(ok) / len(pousadas), 1) if pousadas else None,
            })
        return resultado

    def carregar_cenario(self, nome, semente=None):
        rnd = random.Random(semente)
        aeroportos = ["GRU", "GIG", "BSB", "CNF", "POA", "REC", "SSA", "FLN", "CWB", "FOR"]
        companhias = ["AZU", "GLO", "TAM", "PTB", "ONE"]
        cenarios = {
            "Horário de pico (muitos voos comerciais)": {
                "Voo comercial regular": 10, "Condições meteorológicas adversas": 1,
                "Combustível baixo": 1,
            },
            "Tempestade (clima adverso)": {
                "Condições meteorológicas adversas": 6, "Voo comercial regular": 3,
                "Combustível baixo": 2,
            },
            "Múltiplas emergências": {
                "Emergência médica a bordo": 2, "Falha mecânica / pane": 1,
                "Combustível baixo": 2, "Voo comercial regular": 4,
            },
        }
        if nome not in cenarios:
            raise ValueError(f"Cenário desconhecido: {nome}")
        motivos = [m for m, qtd in cenarios[nome].items() for _ in range(qtd)]
        rnd.shuffle(motivos)
        self._banco.registrar_log("CENARIO", "-", f"Cenário carregado: {nome}")
        criadas = []
        for motivo in motivos:
            origem, destino = rnd.sample(aeroportos, 2)
            codigo = f"{rnd.choice(companhias)}{rnd.randint(100, 9999)}"
            criadas.append(self.cadastrar_aeronave(codigo, origem, destino, motivo))
            self._relogio.avancar(rnd.choice([0, 0.5, 1]))
        return criadas

    @staticmethod
    def cenarios_disponiveis():
        return [
            "Horário de pico (muitos voos comerciais)",
            "Tempestade (clima adverso)",
            "Múltiplas emergências",
        ]

    @staticmethod
    def motivos_disponiveis():
        return list(PRIORIDADES.keys())
