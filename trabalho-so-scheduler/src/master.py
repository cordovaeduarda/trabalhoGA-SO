"""
Master node — produtor-consumidor com fila de PODs e threads de Workers.
"""
import threading
import time
from queue import Empty, Queue
from typing import List

from models import POD, Worker
from scheduler import CustomScheduler, DefaultScheduler


class Master:
    """
    Master orquestra:
      - uma fila compartilhada de PODs pendentes (produtor-consumidor)
      - threads consumidoras: uma para o scheduler e outras para liberação
    """

    def __init__(self, workers: List[Worker], scheduler) -> None:
        self.workers = workers
        self.scheduler = scheduler
        self.queue: "Queue[POD]" = Queue()
        self.pending: List[POD] = []           # PODs que não couberam ainda
        self.history: List[POD] = []           # todos os PODs já processados
        self.stop_event = threading.Event()
        self.lock = threading.Lock()

    # ---------- produtor ----------
    def submit(self, pod: POD) -> None:
        """Produtor: enfileira um POD para ser escalonado."""
        self.queue.put(pod)

    # ---------- consumidor (scheduler loop) ----------
    def _scheduler_loop(self) -> None:
        while not self.stop_event.is_set():
            try:
                pod = self.queue.get(timeout=0.2)
            except Empty:
                # tenta reescalonar PODs pendentes
                self._retry_pending()
                continue

            chosen = self.scheduler.pick(pod, self.workers)
            if chosen and chosen.allocate(pod):
                print(f"[SCHED:{self.scheduler.name}] {pod.pod_id} -> {chosen.worker_id}")
                # dispara thread que simula execução do POD
                threading.Thread(
                    target=self._run_pod, args=(chosen, pod), daemon=True
                ).start()
            else:
                pod.status = "Pending"
                with self.lock:
                    self.pending.append(pod)
                print(f"[SCHED:{self.scheduler.name}] {pod.pod_id} -> Pending (sem recursos)")

            with self.lock:
                self.history.append(pod)
            self.queue.task_done()

    def _retry_pending(self) -> None:
        with self.lock:
            still_pending = []
            for pod in self.pending:
                chosen = self.scheduler.pick(pod, self.workers)
                if chosen and chosen.allocate(pod):
                    print(f"[SCHED:{self.scheduler.name}] {pod.pod_id} (retry) -> {chosen.worker_id}")
                    threading.Thread(
                        target=self._run_pod, args=(chosen, pod), daemon=True
                    ).start()
                else:
                    still_pending.append(pod)
            self.pending = still_pending

    def _run_pod(self, worker: Worker, pod: POD) -> None:
        """Simula execução do POD e libera recursos ao final."""
        time.sleep(pod.duration)
        worker.release(pod)
        print(f"[RUN] {pod.pod_id} concluído em {worker.worker_id}")

    # ---------- ciclo de vida ----------
    def start(self) -> None:
        self.thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        self.thread.join(timeout=2)

    def wait_idle(self, timeout: float = 30.0) -> None:
        """Espera fila vazia, pendentes vazios e nenhum POD ainda em Running."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            running = sum(
                1 for p in self.history if p.status == "Running"
            )
            with self.lock:
                pending_n = len(self.pending)
            if self.queue.empty() and pending_n == 0 and running == 0:
                return
            time.sleep(0.2)
