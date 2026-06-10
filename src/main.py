"""
Ponto de entrada: cria cluster, gera PODs e executa simulação comparativa
entre o escalonador padrão (default) e o customizado (multi-métrica).

Cenário: 20 PODs heterogêneos, sendo vários com SLA de latência apertado
(<= 10 ms) — apenas o worker-1 atende. Isso evidencia a diferença entre
o escalonador padrão (que ignora latência e viola SLA) e o customizado
(que respeita SLA, mesmo que isso gere mais Pendings).

Uso:
    python main.py default
    python main.py custom
    python main.py compare
"""
import random
import sys
from typing import List

from master import Master
from models import POD, Worker
from scheduler import CustomScheduler, DefaultScheduler
from visualizer import print_cluster_state, print_statistics


def build_workers() -> List[Worker]:
    """3 Workers heterogêneos com latências bem distintas."""
    return [
        Worker("worker-1", cpu_total=8,  mem_total=8192,  disk_total=50_000, latency=5),
        Worker("worker-2", cpu_total=4,  mem_total=16_384, disk_total=20_000, latency=25),
        Worker("worker-3", cpu_total=16, mem_total=4096,  disk_total=100_000, latency=60),
    ]


def build_pods(n: int = 20, seed: int = 42) -> List[POD]:
    """
    Gera n PODs com requisitos variados.

    ~40% dos PODs têm SLA de latência apertado (<=10 ms) — só o worker-1 atende.
    O DefaultScheduler vai ignorar isso e alocar em qualquer Worker, gerando
    violações; o CustomScheduler vai respeitar e usar Pending quando preciso.
    """
    rng = random.Random(seed)
    pods = []
    for i in range(n):
        # 40% dos PODs com SLA apertado
        strict_sla = rng.random() < 0.4
        max_lat = 10 if strict_sla else rng.choice([30, 50, 100])

        pods.append(POD(
            pod_id=f"pod-{i:02d}",
            cpu_req=rng.choice([0.5, 1, 2, 3]),
            mem_req=rng.choice([256, 512, 1024, 2048]),
            disk_req=rng.choice([500, 1000, 5000, 10_000]),
            max_latency=max_lat,
            duration=rng.uniform(1.0, 2.5),
        ))
    return pods


def run(scheduler) -> dict:
    workers = build_workers()
    pods = build_pods(n=20)

    print(f"\n############ Iniciando simulação com {scheduler.name} ############")
    print_cluster_state(workers, "Estado inicial")

    master = Master(workers, scheduler)
    master.start()
    for pod in pods:
        master.submit(pod)
    master.wait_idle(timeout=60)
    master.stop()

    print_cluster_state(workers, "Estado final")
    return print_statistics(master.history, master.pending, scheduler.name)


def compare() -> None:
    stats_default = run(DefaultScheduler())
    stats_custom = run(CustomScheduler())

    print("\n############ COMPARAÇÃO ############")
    print(f"{'Métrica':<32}{'Default':>12}{'Custom':>12}")
    print("-" * 56)
    print(f"{'Taxa alocação (%)':<32}{stats_default['rate']:>12.1f}{stats_custom['rate']:>12.1f}")
    print(f"{'PODs alocados':<32}{stats_default['allocated']:>12}{stats_custom['allocated']:>12}")
    print(f"{'PODs Pending':<32}{stats_default['pending']:>12}{stats_custom['pending']:>12}")
    print(f"{'⚠️  Violações SLA latência':<32}{stats_default['sla_violations']:>12}{stats_custom['sla_violations']:>12}")
    print(f"\nDistribuição Default: {stats_default['by_worker']}")
    print(f"Distribuição Custom : {stats_custom['by_worker']}")

    print("\n=== Análise ===")
    if stats_default['sla_violations'] > stats_custom['sla_violations']:
        print(f"✅ O CustomScheduler eliminou {stats_default['sla_violations']} violações de SLA")
        print(f"   que o DefaultScheduler cometeria.")
    if stats_custom['pending'] > stats_default['pending']:
        print(f"ℹ️  O CustomScheduler usou Pending {stats_custom['pending']} vez(es) a mais")
        print(f"   — trade-off consciente para respeitar SLA de latência.")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "compare"
    if mode == "default":
        run(DefaultScheduler())
    elif mode == "custom":
        run(CustomScheduler())
    else:
        compare()
