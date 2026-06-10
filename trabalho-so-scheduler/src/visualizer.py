"""
Funções de visualização do estado do cluster (texto ASCII)
e estatísticas finais.
"""
from typing import List

from models import POD, Worker


def _bar(used: float, total: float, width: int = 20) -> str:
    pct = 0 if total == 0 else used / total
    filled = int(pct * width)
    return "[" + "#" * filled + "." * (width - filled) + f"] {used:.1f}/{total:.1f}"


def print_cluster_state(workers: List[Worker], title: str = "Cluster State") -> None:
    print(f"\n=== {title} ===")
    for w in workers:
        print(f"\nWorker {w.worker_id}  (latency={w.latency} ms)")
        print(f"  CPU  {_bar(w.cpu_used, w.cpu_total)}")
        print(f"  MEM  {_bar(w.mem_used, w.mem_total)} MB")
        print(f"  DISK {_bar(w.disk_used, w.disk_total)} MB")
        if w.pods:
            running = [p.pod_id for p in w.pods if p.status == "Running"]
            done = [p.pod_id for p in w.pods if p.status == "Completed"]
            violated = [p.pod_id for p in w.pods if p.sla_violated]
            print(f"  PODs running   : {running}")
            print(f"  PODs concluídos: {done}")
            if violated:
                print(f"  ⚠️  PODs com SLA de latência violado: {violated}")


def print_statistics(history: List[POD], pending: List[POD], scheduler_name: str) -> dict:
    total = len(history)
    allocated = sum(1 for p in history if p.worker_id)
    pending_n = len(pending)
    sla_violations = sum(1 for p in history if p.sla_violated)
    rate = (allocated / total * 100) if total else 0.0

    by_worker: dict = {}
    for p in history:
        if p.worker_id:
            by_worker[p.worker_id] = by_worker.get(p.worker_id, 0) + 1

    print(f"\n=== Estatísticas ({scheduler_name}) ===")
    print(f"Total de PODs submetidos    : {total}")
    print(f"PODs alocados               : {allocated}")
    print(f"PODs em Pending             : {pending_n}")
    print(f"⚠️  Violações de SLA latência: {sla_violations}")
    print(f"Taxa de alocação            : {rate:.1f}%")
    print(f"Distribuição por Worker     : {by_worker}")
    return {
        "scheduler": scheduler_name,
        "total": total,
        "allocated": allocated,
        "pending": pending_n,
        "sla_violations": sla_violations,
        "rate": rate,
        "by_worker": by_worker,
    }
