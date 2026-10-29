"""Regras de negócio do simulador (dicionário de prioridades, SLA e aging)."""

# Situação da aeronave -> prioridade base (1 = mais urgente, 4 = menos urgente)
PRIORIDADES = {
    "Emergência médica a bordo": 1,
    "Falha mecânica / pane": 1,
    "Combustível baixo": 2,
    "Condições meteorológicas adversas": 3,
    "Voo comercial regular": 4,
}

# SLA: tempo máximo de espera (em minutos simulados) para cada nível de prioridade
SLA_MINUTOS = {
    1: 2,
    2: 5,
    3: 10,
    4: 15,
}

# Aging: a cada 5 minutos de espera a prioridade melhora 1 nível,
# mas nunca chega ao nível 1, que é reservado para emergências
AGING_INTERVALO_MIN = 5
PRIORIDADE_MINIMA_AGING = 2

# Tempo em que a pista fica ocupada a cada pouso
TEMPO_POUSO_MIN = 2
