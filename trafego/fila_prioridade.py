import heapq


class FilaDePrioridade:
    def __init__(self):
        self._heap = []

    def inserir(self, aeronave):
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
