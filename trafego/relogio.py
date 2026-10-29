class RelogioSimulado:
    def __init__(self, inicio=0.0):
        self._minuto = float(inicio)

    def agora(self):
        return self._minuto

    def avancar(self, minutos):
        if minutos < 0:
            raise ValueError("Não é possível voltar no tempo.")
        self._minuto += minutos
