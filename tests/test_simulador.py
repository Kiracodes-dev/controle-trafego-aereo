import unittest

from trafego.banco_dados import BancoDeDados
from trafego.controle import ControleTrafegoAereo


class TestSimulador(unittest.TestCase):
    def setUp(self):
        self.banco = BancoDeDados(":memory:")
        self.controle = ControleTrafegoAereo(self.banco)

    def eventos(self):
        return [l.evento for l in self.banco.listar_logs()]

    def test_emergencia_pousa_primeiro(self):
        self.controle.cadastrar_aeronave("AAA100", "GRU", "FLN", "Voo comercial regular")
        self.controle.cadastrar_aeronave("BBB200", "GIG", "FLN", "Emergência médica a bordo")
        self.assertEqual(self.controle.processar_pouso().codigo, "BBB200")

    def test_desempate_por_ordem_de_chegada(self):
        self.controle.cadastrar_aeronave("PRIMEIRO", "GRU", "FLN", "Voo comercial regular")
        self.controle.relogio.avancar(1)
        self.controle.cadastrar_aeronave("SEGUNDO", "GRU", "FLN", "Voo comercial regular")
        self.assertEqual(self.controle.processar_pouso().codigo, "PRIMEIRO")

    def test_aging_melhora_prioridade_ate_nivel_2(self):
        a = self.controle.cadastrar_aeronave("AAA100", "GRU", "FLN", "Voo comercial regular")
        self.assertEqual(a.prioridade_atual(), 4)
        self.controle.avancar_tempo(5)
        self.assertEqual(a.prioridade_atual(), 3)
        self.controle.avancar_tempo(60)
        self.assertEqual(a.prioridade_atual(), 2)
        self.assertIn("ALTERACAO_PRIORIDADE", self.eventos())

    def test_aging_evita_starvation(self):
        self.controle.cadastrar_aeronave("ANTIGO", "GRU", "FLN", "Voo comercial regular")
        self.controle.avancar_tempo(10)
        self.controle.cadastrar_aeronave("NOVO", "GRU", "FLN", "Condições meteorológicas adversas")
        self.assertEqual(self.controle.processar_pouso().codigo, "ANTIGO")

    def test_emergencia_nunca_e_ultrapassada_pelo_aging(self):
        self.controle.cadastrar_aeronave("ANTIGO", "GRU", "FLN", "Voo comercial regular")
        self.controle.avancar_tempo(120)
        self.controle.cadastrar_aeronave("EMERG", "GRU", "FLN", "Falha mecânica / pane")
        self.assertEqual(self.controle.processar_pouso().codigo, "EMERG")

    def test_empate_favorece_urgencia_original(self):
        self.controle.cadastrar_aeronave("COMERCIAL", "GRU", "FLN", "Voo comercial regular")
        self.controle.avancar_tempo(10)
        self.controle.cadastrar_aeronave("COMBUSTIVEL", "GRU", "FLN", "Combustível baixo")
        self.assertEqual(self.controle.processar_pouso().codigo, "COMBUSTIVEL")

    def test_fila_vazia(self):
        self.assertIsNone(self.controle.processar_pouso())

    def test_remover_aguardando(self):
        self.controle.cadastrar_aeronave("AAA100", "GRU", "FLN", "Voo comercial regular")
        self.controle.cadastrar_aeronave("BBB200", "GRU", "FLN", "Combustível baixo")
        self.assertEqual(self.controle.remover_aeronaves_aguardando(), 2)
        self.assertEqual(self.controle.metricas()["aguardando"], 0)

    def test_metricas_e_sla(self):
        self.controle.cadastrar_aeronave("AAA100", "GRU", "FLN", "Combustível baixo")
        self.controle.avancar_tempo(3)
        self.controle.processar_pouso()
        self.controle.cadastrar_aeronave("BBB200", "GRU", "FLN", "Emergência médica a bordo")
        self.controle.avancar_tempo(4)
        self.controle.processar_pouso()
        m = self.controle.metricas()
        self.assertEqual(m["pousadas"], 2)
        self.assertAlmostEqual(m["atendimento_medio"], 3.5)
        self.assertAlmostEqual(m["sla_cumprido_pct"], 50.0)

    def test_logs_registrados(self):
        self.controle.cadastrar_aeronave("AAA100", "GRU", "FLN", "Voo comercial regular")
        self.controle.processar_pouso()
        self.assertEqual(set(self.eventos()), {"CADASTRO", "POUSO_AUTORIZADO"})

    def test_motivo_invalido(self):
        with self.assertRaises(ValueError):
            self.controle.cadastrar_aeronave("AAA100", "GRU", "FLN", "Motivo inventado")

    def test_cenarios_carregam(self):
        for nome in ControleTrafegoAereo.cenarios_disponiveis():
            self.assertGreater(len(self.controle.carregar_cenario(nome, semente=1)), 0)


if __name__ == "__main__":
    unittest.main()
