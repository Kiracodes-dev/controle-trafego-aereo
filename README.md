# ✈️ Simulador de Controle de Tráfego Aéreo

Simulador orientado a objetos que organiza aeronaves aguardando autorização de pouso usando
**fila de prioridade (heapq)**, **aging** contra *starvation*, **métricas de SLA** e
**logs de auditoria em SQLite**. Interface feita em **Streamlit**.

Projeto da A3 — Soluções Computacionais (1ª versão / protótipo).

## Como executar

```bash
pip install -r requirements.txt
streamlit run app.py
```

O navegador abre em `http://localhost:8501`.

Testes automatizados:

```bash
python -m unittest -v
```


- Cadastro de aeronaves (código, origem, destino e situação).
- Fila de pouso ordenada por prioridade, com desempate por urgência original e ordem de chegada.
- Botão **Autorizar próximo pouso** (cada pouso ocupa a pista por 2 minutos simulados).
- **Relógio simulado**: avance o tempo para ver o aging e o SLA funcionando sem esperar minutos reais.
- **Cenários prontos**: horário de pico, tempestade e múltiplas emergências.
- Métricas: aeronaves aguardando, espera média e máxima, tempo médio de atendimento, % de SLA cumprido
  (geral e por prioridade) e alerta de aeronaves fora do SLA.
- Logs de cadastro, alteração de prioridade (aging), pousos, remoções e cenários, com filtro e exportação CSV.



| Situação | Prioridade | SLA (espera máx.) |
|---|---|---|
| Emergência médica a bordo | 1 | 2 min |
| Falha mecânica / pane | 1 | 2 min |
| Combustível baixo | 2 | 5 min |
| Condições meteorológicas adversas | 3 | 10 min |
| Voo comercial regular | 4 | 15 min |

- Número menor = atendido primeiro.
- **Aging:** a cada 5 minutos de espera o voo sobe 1 nível, até no máximo o nível 2.
  O nível 1 é exclusivo de emergências (regra de segurança).
- **Desempate:** mesma prioridade atual → vence o voo com urgência original maior; depois, quem chegou primeiro.


```
app.py                      InterfaceStreamlit
trafego/aeronave.py         Aeronave
trafego/controle.py         ControleTrafegoAereo
trafego/fila_prioridade.py  FilaDePrioridade (heapq)
trafego/banco_dados.py      BancoDeDados + LogAuditoria (SQLite)
trafego/regras.py           dicionário de prioridades, SLA e aging
trafego/relogio.py          RelogioSimulado
tests/test_simulador.py     testes automatizados
```
