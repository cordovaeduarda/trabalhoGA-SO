# Trabalho I — Análise e Aplicação de Sistemas Operacionais

Simulador de um cluster estilo **Kubernetes** (1 Master + N Workers) com um
escalonador de PODs **multi-critério** próprio, comparado ao escalonador
padrão do K8s.

> **Disciplina:** Sistemas Operacionais: Análise e Aplicações
> **Aluno:** _Eduarda Barth Cordova_

---

## 🎯 Objetivo

Cumprir os requisitos do enunciado `TrabalhoI_2026_01_LS.pdf`:

- Criar **1 Master** e **≥ 2 Workers** com capacidades computacionais.
- Gerar **mais de uma dezena de PODs** com requisitos heterogêneos.
- Implementar um algoritmo de escalonamento com **≥ 3 métricas** (o
  K8s padrão usa apenas CPU + memória; aqui usamos **4**: CPU, memória,
  **disco** e **latência de rede**).
- Mostrar onde os PODs foram alocados e os recursos livres/ocupados.
- Comparar com o escalonador padrão.

## 🧱 Arquitetura

```
                      submit(pod)
   +--------+   ───────────────▶   +---------- MASTER ----------+
   | gerador|                      |  Queue (produtor-consumidor)|
   +--------+                      |  Scheduler thread           |
                                   +-----+-----------+-----------+
                                         │  pick()   │
                              ┌──────────┼───────────┼──────────┐
                              ▼          ▼           ▼
                          Worker-1   Worker-2    Worker-3
                          (thread    (thread     (thread
                           lock +     lock +      lock +
                           run pod)   run pod)    run pod)
```

Conceitos da disciplina exercitados:

| Conceito                | Onde aparece                                                  |
|-------------------------|---------------------------------------------------------------|
| Shell script            | `run.sh` orquestra execução e logs                            |
| Processos               | Cada execução `python3 main.py …` é um processo               |
| Threads                 | `Master._scheduler_loop` e uma thread por POD em execução     |
| Produtor-consumidor     | `queue.Queue` entre `submit()` (produtor) e o loop (consumidor) |
| Sincronização           | `threading.Lock` por Worker, `Lock` global do Master          |

## 📐 Algoritmo de escalonamento custom

Para cada POD, o `CustomScheduler` filtra Workers que **cabem** o POD
(CPU, memória, disco e latência ≤ tolerada) e escolhe o de **maior score**:

```
score = w_cpu  * (cpu_free  / cpu_total)
      + w_mem  * (mem_free  / mem_total)
      + w_disk * (disk_free / disk_total)
      - w_lat  * (latency   / pod.max_latency)
```

Pesos default: `0.30 / 0.25 / 0.25 / 0.20`.

## ▶️ Como executar

Requisitos: **Python ≥ 3.9** (apenas biblioteca padrão).

```bash
# Modo comparativo (padrão)
./run.sh

# Ou diretamente:
cd src
python3 main.py default     # apenas escalonador padrão
python3 main.py custom      # apenas escalonador customizado
python3 main.py compare     # ambos + comparação
```

## 📊 Saída esperada

- Estado inicial e final de cada Worker (CPU/MEM/DISK como barras).
- Log de cada decisão `[SCHED:<nome>] pod-XX -> worker-Y`.
- Estatísticas: total de PODs, alocados, em Pending, taxa, distribuição.
- Tabela comparativa Default × Custom.

## 🗂️ Estrutura

```
trabalho-so-scheduler/
├── README.md
├── run.sh
└── src/
    ├── main.py          # entrada + comparação
    ├── master.py        # Master + fila + threads
    ├── models.py        # Worker e POD
    ├── scheduler.py     # DefaultScheduler e CustomScheduler
    └── visualizer.py    # estado e estatísticas
```

## 🎬 Vídeo

Link do vídeo (10 min): _https://drive.google.com/file/d/1EmAtELIOYGveW7nE6z3w5ZBjJIa66EyE/view?usp=sharing_

## 📄 Licença

Uso acadêmico — Unisinos 2026/01.
