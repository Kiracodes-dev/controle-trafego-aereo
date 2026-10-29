"""Classe ControleTrafegoAereo: coordena aeronaves, fila, pousos e métricas."""

import random

from trafego.aeronave import Aeronave
from trafego.fila_prioridade import FilaDePrioridade
from trafego.regras import PRIORIDADES, SLA_MINUTOS, TEMPO_POUSO_MIN
from trafego.relogio import RelogioSimulado

# Quantidade de aeronaves de cada situação em cada cenário de teste
CENARIOS = {
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
    "Neblina com combustível crítico": {
        "Combustível baixo": 5, "Condições meteorológicas adversas": 4,
        "Voo comercial regular": 3,
    },
    "Pista sobrecarregada (fila longa)": {
        "Voo comercial regular": 14, "Condições meteorológicas adversas": 3,
        "Combustível baixo": 2, "Emergência médica a bordo": 1,
    },
}

# Pesos usados no cenário aleatório: situações comuns aparecem mais vezes
PESOS_ALEATORIO = {
    "Emergência médica a bordo": 1,
    "Falha mecânica / pane": 1,
    "Combustível baixo": 2,
    "Condições meteorológicas adversas": 3,
    "Voo comercial regular": 8,
}
CENARIO_ALEATORIO = "Fluxo aleatório (12 voos)"

AEROPORTOS = ["GRU", "GIG", "BSB", "CNF", "POA", "REC", "SSA", "FLN", "CWB", "FOR"]
COMPANHIAS = ["AZU", "GLO", "TAM", "PTB", "ONE"]


class ControleTrafegoAereo:
    def __init__(self, banco, relogio=None):
        self._banco = banco
        # Retoma a simulação de onde parou: relógio e aeronaves vêm do banco
        self._relogio = relogio or RelogioSimulado(banco.carregar_relogio())
        self._aeronaves = [
            Aeronave.restaurar(dados, self._relogio) for dados in banco.carregar_aeronaves()
        ]

    @property
    def aeronaves(self):
        return list(self._aeronaves)

    @property
    def relogio(self):
        return self._relogio

    def cadastrar_aeronave(self, codigo, origem, destino, motivo):
        aeronave = Aeronave(codigo, origem, destino, motivo, self._relogio)
        self._aeronaves.append(aeronave)
        self._banco.salvar_aeronave(aeronave.para_dict())
        self._banco.registrar_log(
            "CADASTRO",
            aeronave.codigo,
            f"{aeronave.origem}->{aeronave.destino} | {motivo} | prioridade {aeronave.prioridade_base}",
        )
        return aeronave

    def construir_fila(self):
        """Monta a heap com os voos aguardando e registra mudanças de prioridade (aging)."""
        fila = FilaDePrioridade()
        for aeronave in self._aeronaves:
            if aeronave.status != "AGUARDANDO":
                continue
            self._registrar_mudanca_prioridade(aeronave)
            fila.inserir(aeronave)
        return fila

    def processar_pouso(self):
        """Autoriza o pouso da próxima aeronave da fila. A pista fica ocupada
        por TEMPO_POUSO_MIN minutos, então o relógio avança."""
        proxima = self.construir_fila().remover_proxima()
        if proxima is None:
            return None
        proxima.marcar_pousada()
        self._banco.salvar_aeronave(proxima.para_dict())
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
                self._banco.salvar_aeronave(aeronave.para_dict())
                removidas += 1
        self._banco.registrar_log("REMOCAO", "-", f"{removidas} aeronave(s) removida(s) da fila")
        return removidas

    def reiniciar_simulacao(self):
        self._banco.reiniciar()
        self._aeronaves = []
        self._relogio = RelogioSimulado()
        self._banco.registrar_log("REINICIO", "-", "Simulação reiniciada")

    def avancar_tempo(self, minutos):
        self._relogio.avancar(minutos)
        self._banco.salvar_relogio(self._relogio.agora())
        # Reconstrói a fila só para registrar as prioridades que mudaram com o tempo
        self.construir_fila()

    def _registrar_mudanca_prioridade(self, aeronave):
        mudanca = aeronave.atualizar_prioridade_registrada()
        if mudanca is None:
            return
        anterior, atual = mudanca
        self._banco.salvar_aeronave(aeronave.para_dict())
        self._banco.registrar_log(
            "ALTERACAO_PRIORIDADE",
            aeronave.codigo,
            f"aging: prioridade {anterior} -> {atual} após {aeronave.tempo_espera():.1f} min de espera",
        )

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
            # Sem pousos ainda, nenhum SLA foi descumprido
            "sla_cumprido_pct": 100 * len(dentro_sla) / len(pousadas) if pousadas else 100.0,
            "aguardando_fora_sla": len(estourando),
        }

    def sla_por_prioridade(self):
        """Cumprimento do SLA agrupado por nível de prioridade base."""
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
        if nome == CENARIO_ALEATORIO:
            motivos = rnd.choices(list(PESOS_ALEATORIO), weights=PESOS_ALEATORIO.values(), k=12)
        elif nome in CENARIOS:
            motivos = [m for m, qtd in CENARIOS[nome].items() for _ in range(qtd)]
            rnd.shuffle(motivos)
        else:
            raise ValueError(f"Cenário desconhecido: {nome}")
        self._banco.registrar_log("CENARIO", "-", f"Cenário carregado: {nome}")
        criadas = []
        for motivo in motivos:
            origem, destino = rnd.sample(AEROPORTOS, 2)
            codigo = f"{rnd.choice(COMPANHIAS)}{rnd.randint(100, 9999)}"
            criadas.append(self.cadastrar_aeronave(codigo, origem, destino, motivo))
            # Espaça as chegadas em 0 a 1 minuto, como numa fila real
            self._relogio.avancar(rnd.choice([0, 0.5, 1]))
        self._banco.salvar_relogio(self._relogio.agora())
        return criadas

    @staticmethod
    def cenarios_disponiveis():
        return list(CENARIOS) + [CENARIO_ALEATORIO]

    @staticmethod
    def motivos_disponiveis():
        return list(PRIORIDADES.keys())
