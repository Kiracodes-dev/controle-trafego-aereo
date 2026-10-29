"""InterfaceStreamlit: tela do simulador. Execute com:  streamlit run app.py"""

import pandas as pd
import streamlit as st

from trafego.banco_dados import BancoDeDados
from trafego.controle import ControleTrafegoAereo
from trafego.regras import PRIORIDADES, SLA_MINUTOS

NOMES_PRIORIDADE = {1: "1 - Emergência", 2: "2 - Alta", 3: "3 - Média", 4: "4 - Normal"}


class InterfaceStreamlit:
    def inicializar_sistema(self):
        st.set_page_config(page_title="Controle de Tráfego Aéreo", page_icon="✈️", layout="wide")
        # session_state mantém o controlador vivo entre as atualizações da página
        if "controle" not in st.session_state:
            banco = BancoDeDados("trafego_aereo.db")
            st.session_state.banco = banco
            st.session_state.controle = ControleTrafegoAereo(banco)
            st.session_state.ultimo_pouso = None
        self.banco = st.session_state.banco
        self.controle = st.session_state.controle

    def exibir_painel_lateral(self):
        with st.sidebar:
            st.header("🛬 Nova solicitação de pouso")
            with st.form("cadastro", clear_on_submit=True):
                codigo = st.text_input("Código do voo", placeholder="ex.: AZU4521")
                c1, c2 = st.columns(2)
                origem = c1.text_input("Origem", placeholder="GRU")
                destino = c2.text_input("Destino", placeholder="FLN")
                motivo = st.selectbox(
                    "Situação da aeronave",
                    list(PRIORIDADES.keys()),
                    index=len(PRIORIDADES) - 1,
                    format_func=lambda m: f"{m} (P{PRIORIDADES[m]})",
                )
                if st.form_submit_button("Cadastrar aeronave", use_container_width=True):
                    try:
                        a = self.controle.cadastrar_aeronave(codigo, origem or "---", destino or "---", motivo)
                        st.success(f"{a.codigo} entrou na fila com prioridade {a.prioridade_base}.")
                    except ValueError as erro:
                        st.error(str(erro))

            st.divider()
            st.header("🎬 Cenários de teste")
            cenario = st.selectbox("Cenário", ControleTrafegoAereo.cenarios_disponiveis())
            if st.button("Carregar cenário", use_container_width=True):
                criadas = self.controle.carregar_cenario(cenario)
                st.success(f"{len(criadas)} aeronaves adicionadas.")

            st.divider()
            st.header("⏱️ Relógio simulado")
            minutos = st.number_input("Minutos", min_value=1, max_value=60, value=5)
            if st.button(f"Avançar {minutos} min", use_container_width=True):
                self.controle.avancar_tempo(minutos)

            st.divider()
            if st.button("Remover todas aguardando", use_container_width=True):
                n = self.controle.remover_aeronaves_aguardando()
                st.warning(f"{n} aeronave(s) removida(s).")
            if st.button("Reiniciar simulação", use_container_width=True,
                         help="Apaga aeronaves, relógio e logs salvos no banco"):
                self.controle.reiniciar_simulacao()
                st.session_state.ultimo_pouso = None
                st.rerun()

            with st.expander("Regras de prioridade e SLA"):
                st.markdown(
                    "\n".join(f"- **{m}** → P{p} (SLA {SLA_MINUTOS[p]} min)" for m, p in PRIORIDADES.items())
                    + "\n\n**Aging:** a cada 5 min de espera o voo sobe 1 nível, até no máximo P2 "
                      "(P1 é exclusivo de emergências). Cada pouso ocupa a pista por 2 min."
                )

    def exibir_metricas(self):
        m = self.controle.metricas()
        st.caption(f"🕒 Relógio da simulação: **{self.controle.relogio.agora():.1f} min**")
        # Duas linhas de três cartões para os números não ficarem cortados em telas menores
        linha1 = st.columns(3)
        linha1[0].metric("Aguardando", m["aguardando"])
        linha1[1].metric("Pousos", m["pousadas"])
        linha1[2].metric("SLA cumprido", f"{m['sla_cumprido_pct']:.0f}%")
        linha2 = st.columns(3)
        linha2[0].metric("Espera média", f"{m['espera_media']:.1f} min")
        linha2[1].metric("Espera máxima", f"{m['espera_maxima']:.1f} min")
        linha2[2].metric("Atendimento médio", f"{m['atendimento_medio']:.1f} min")
        if m["aguardando_fora_sla"]:
            st.error(f"⚠️ {m['aguardando_fora_sla']} aeronave(s) aguardando já passaram do SLA.")

    def exibir_fila(self):
        st.subheader("📋 Fila de pouso (ordem de atendimento)")
        fila = self.controle.construir_fila().obter_ordenada()
        if st.button("✅ Autorizar próximo pouso", type="primary", disabled=not fila):
            st.session_state.ultimo_pouso = self.controle.processar_pouso()
            st.rerun()
        if st.session_state.ultimo_pouso:
            a = st.session_state.ultimo_pouso
            st.info(f"Último pouso autorizado: **{a.codigo}** ({a.motivo}) após {a.tempo_espera():.1f} min.")
        if not fila:
            st.success("Não há aeronaves aguardando autorização de pouso.")
            return
        linhas = []
        for posicao, a in enumerate(fila, start=1):
            sla = SLA_MINUTOS[a.prioridade_base]
            linhas.append({
                "Posição": posicao,
                "Voo": a.codigo,
                "Rota": f"{a.origem} → {a.destino}",
                "Situação": a.motivo,
                "Prioridade base": a.prioridade_base,
                "Prioridade atual": NOMES_PRIORIDADE[a.prioridade_atual()],
                "Aging": "⬆️" if a.prioridade_atual() < a.prioridade_base else "",
                "Espera (min)": round(a.tempo_espera(), 1),
                "SLA (min)": sla,
                "SLA": "🔴 estourado" if a.tempo_espera() > sla else "🟢 ok",
            })
        st.dataframe(pd.DataFrame(linhas), hide_index=True, use_container_width=True)

    def exibir_historico(self):
        st.subheader("🛬 Histórico de pousos")
        pousadas = sorted(
            (a for a in self.controle.aeronaves if a.status == "POUSOU"), key=lambda a: a.pousou_em
        )
        if not pousadas:
            st.write("Nenhum pouso realizado ainda.")
            return
        df = pd.DataFrame([{
            "Voo": a.codigo,
            "Situação": a.motivo,
            "Prioridade base": a.prioridade_base,
            "Pousou no minuto": round(a.pousou_em, 1),
            "Esperou (min)": round(a.tempo_espera(), 1),
            "Dentro do SLA": "sim" if a.tempo_espera() <= SLA_MINUTOS[a.prioridade_base] else "não",
        } for a in pousadas])
        st.dataframe(df, hide_index=True, use_container_width=True)

        sla = pd.DataFrame(self.controle.sla_por_prioridade())
        col_graf1, col_graf2 = st.columns(2)
        with col_graf1:
            st.markdown("**Cumprimento do SLA por prioridade (%)**")
            # Prioridades sem nenhum pouso ficam de fora do gráfico
            grafico_sla = sla.dropna(subset=["cumprimento_pct"])
            grafico_sla = grafico_sla.assign(prioridade=grafico_sla["prioridade"].map(NOMES_PRIORIDADE))
            st.bar_chart(grafico_sla, x="prioridade", y="cumprimento_pct", y_label="% dentro do SLA")
        with col_graf2:
            st.markdown("**Tempo de espera de cada pouso x SLA (min)**")
            espera = pd.DataFrame({
                "Voo": [a.codigo for a in pousadas],
                "Esperou": [round(a.tempo_espera(), 1) for a in pousadas],
                "SLA": [SLA_MINUTOS[a.prioridade_base] for a in pousadas],
            })
            st.bar_chart(espera, x="Voo", y=["Esperou", "SLA"], stack=False, y_label="minutos")

        st.markdown("**Cumprimento do SLA por prioridade**")
        st.dataframe(sla, hide_index=True)

    def exibir_logs(self):
        st.subheader("🗂️ Logs de auditoria (SQLite)")
        logs = self.banco.listar_logs()
        if not logs:
            st.write("Nenhum evento registrado.")
            return
        df = pd.DataFrame([vars(l) for l in logs])
        eventos = st.multiselect("Filtrar eventos", sorted(df["evento"].unique()))
        if eventos:
            df = df[df["evento"].isin(eventos)]
        st.dataframe(df, hide_index=True, use_container_width=True)
        st.download_button(
            "⬇️ Exportar logs (CSV)", df.to_csv(index=False).encode("utf-8-sig"),
            "logs_trafego_aereo.csv", "text/csv",
        )

    def executar(self):
        self.inicializar_sistema()
        st.title("✈️ Simulador de Controle de Tráfego Aéreo")
        st.write("Fila de prioridade com aging para organizar as autorizações de pouso.")
        self.exibir_painel_lateral()
        self.exibir_metricas()
        aba_fila, aba_hist, aba_logs = st.tabs(["Fila", "Histórico e SLA", "Logs"])
        with aba_fila:
            self.exibir_fila()
        with aba_hist:
            self.exibir_historico()
        with aba_logs:
            self.exibir_logs()


InterfaceStreamlit().executar()
