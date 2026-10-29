"""Classe FilaDePrioridade: heap (heapq) ordenada por (prioridade, chegada)."""

import heapq


class FilaDePrioridade:
    def __init__(self):
        self._heap = []

    def inserir(self, aeronave):
        # Ordem da tupla: prioridade atual, depois urgência original (um voo promovido
        # pelo aging não passa na frente de um com combustível baixo), depois ordem de chegada.
        # O id evita que o Python tente comparar dois objetos Aeronave.
        heapq.heappush(
            self._heap,
            (aeronave.prioridade_atual(), aeronave.prioridade_base,
             aeronave.criada_em, aeronave.id, aeronave),
        )

    def obter_ordenada(self):
        return [item[-1] for item in sorted(self._heap)]

    def remover_proxima(self):
        if not self._heap:
            return None
        return heapq.heappop(self._heap)[-1]

    def __len__(self):
        return len(self._heap)
