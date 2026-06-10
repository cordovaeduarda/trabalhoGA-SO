"""
Algoritmos de escalonamento.

- DefaultScheduler  : imita o K8s padrão (CPU + memória apenas — IGNORA
                      disco e latência ao filtrar Workers).
- CustomScheduler   : usa 4 métricas — CPU, memória, DISCO e LATÊNCIA — com
                      score ponderado (multi-critério).
"""
from typing import List, Optional

from models import POD, Worker


class DefaultScheduler:
    """
    Estratégia 'least-allocated' considerando apenas CPU + memória.
    Ignora disco e latência — comportamento equivalente ao kube-scheduler
    quando o POD não declara ephemeral-storage nem topologySpreadConstraints
    de latência.
    """

    name = "default-k8s"

    def pick(self, pod: POD, workers: List[Worker]) -> Optional[Worker]:
        # filtro: SOMENTE CPU e memória
        candidates = [
            w for w in workers
            if pod.cpu_req <= w.cpu_free and pod.mem_req <= w.mem_free
        ]
        if not candidates:
            return None
        # melhor score = mais recursos livres relativos (CPU + MEM)
        return max(
            candidates,
            key=lambda w: (w.cpu_free / w.cpu_total) + (w.mem_free / w.mem_total),
        )


class CustomScheduler:
    """
    Escalonador multi-critério.

    Score = w_cpu  * (cpu_free  / cpu_total)
          + w_mem  * (mem_free  / mem_total)
          + w_disk * (disk_free / disk_total)
          - w_lat  * (latency   / max_latency)

    Quanto maior o score, melhor o Worker. Pesos podem ser ajustados.
    """

    name = "custom-multi-metric"

    def __init__(
        self,
        w_cpu: float = 0.30,
        w_mem: float = 0.25,
        w_disk: float = 0.25,
        w_lat: float = 0.20,
    ) -> None:
        self.w_cpu = w_cpu
        self.w_mem = w_mem
        self.w_disk = w_disk
        self.w_lat = w_lat

    def _score(self, pod: POD, w: Worker) -> float:
        return (
            self.w_cpu * (w.cpu_free / w.cpu_total)
            + self.w_mem * (w.mem_free / w.mem_total)
            + self.w_disk * (w.disk_free / w.disk_total)
            - self.w_lat * (w.latency / max(pod.max_latency, 1e-9))
        )

    def pick(self, pod: POD, workers: List[Worker]) -> Optional[Worker]:
        # filtro completo: CPU, memória, DISCO e LATÊNCIA
        candidates = [w for w in workers if w.can_fit(pod)]
        if not candidates:
            return None
        return max(candidates, key=lambda w: self._score(pod, w))
