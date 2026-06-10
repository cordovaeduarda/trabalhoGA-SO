"""
Estruturas de dados do cluster: Worker e POD.
"""
from dataclasses import dataclass, field
from threading import Lock
from typing import List


@dataclass
class POD:
    """Representa um POD com requisitos computacionais."""
    pod_id: str
    cpu_req: float        # vCPUs requeridas
    mem_req: float        # MB de RAM requeridos
    disk_req: float       # MB de disco requeridos
    max_latency: float    # latência máxima tolerada (ms)
    duration: float       # tempo de execução simulado (s)
    status: str = "Pending"   # Pending | Running | Completed | Failed
    worker_id: str = ""
    sla_violated: bool = False   # marcado True se foi alocado em Worker com latência > max_latency

    def __str__(self) -> str:
        return (f"POD[{self.pod_id} cpu={self.cpu_req} mem={self.mem_req}MB "
                f"disk={self.disk_req}MB lat<={self.max_latency}ms]")


@dataclass
class Worker:
    """Worker node com capacidades computacionais e estado de alocação."""
    worker_id: str
    cpu_total: float
    mem_total: float
    disk_total: float
    latency: float                 # latência média até o Master (ms)
    cpu_used: float = 0.0
    mem_used: float = 0.0
    disk_used: float = 0.0
    pods: List[POD] = field(default_factory=list)
    lock: Lock = field(default_factory=Lock, repr=False)

    # ---------- métricas derivadas ----------
    @property
    def cpu_free(self) -> float:
        return self.cpu_total - self.cpu_used

    @property
    def mem_free(self) -> float:
        return self.mem_total - self.mem_used

    @property
    def disk_free(self) -> float:
        return self.disk_total - self.disk_used

    # ---------- operações ----------
    def can_fit_resources(self, pod: POD) -> bool:
        """Verifica se cabem CPU, memória e disco. NÃO valida latência."""
        return (
            pod.cpu_req <= self.cpu_free
            and pod.mem_req <= self.mem_free
            and pod.disk_req <= self.disk_free
        )

    def can_fit(self, pod: POD) -> bool:
        """Verifica se cabe E respeita latência (validação completa)."""
        return self.can_fit_resources(pod) and self.latency <= pod.max_latency

    def allocate(self, pod: POD) -> bool:
        """
        Aloca o POD reservando recursos. Thread-safe.
        Marca SLA violado se a latência exceder a tolerada — o scheduler
        que chamar é responsável por filtrar antes, se quiser respeitar SLA.
        """
        with self.lock:
            if not self.can_fit_resources(pod):
                return False
            self.cpu_used += pod.cpu_req
            self.mem_used += pod.mem_req
            self.disk_used += pod.disk_req
            pod.worker_id = self.worker_id
            pod.status = "Running"
            pod.sla_violated = self.latency > pod.max_latency
            self.pods.append(pod)
            return True

    def release(self, pod: POD) -> None:
        """Libera os recursos quando o POD termina."""
        with self.lock:
            self.cpu_used -= pod.cpu_req
            self.mem_used -= pod.mem_req
            self.disk_used -= pod.disk_req
            pod.status = "Completed"
