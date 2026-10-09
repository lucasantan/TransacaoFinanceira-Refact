from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from threading import Lock

from .repository import RepositorioContas


@dataclass
class Transacao:
    correlation_id: int
    datetime: datetime
    conta_origem: int
    conta_destino: int
    valor: Decimal

class ServicoTransacao:
    def __init__(self, repositorio: RepositorioContas) -> None:
        self._repositorio = repositorio
        self._locks: dict[int, Lock] = {}
        self._lock_resitro = Lock()

    def _obter_lock(self, numero_conta: int) -> Lock:
        with self._lock_resitro:
            if numero_conta not in self._locks:
                self._locks[numero_conta] = Lock()
            return self._locks[numero_conta]

    def transferir(self, transacao: Transacao) -> None:
        lock = self._obter_lock(transacao.conta_origem)
        with lock:
            origem = self._repositorio.buscar(transacao.conta_origem)
            if origem.saldo < transacao.valor:
                print(f"Transacao numero {transacao.correlation_id} falhou: saldo insuficiente na conta {origem.numero}")
                return
            destino = self._repositorio.buscar(transacao.conta_destino)
            origem.saldo -= transacao.valor
            destino.saldo += transacao.valor
            print(
                f"Transacao numero {transacao.correlation_id} efetivada com sucesso!" 
                f"Novos saldos: Conta Origem: conta: {origem.numero}, saldo: {origem.saldo} | Conta Destino: conta: {destino.numero}, saldo: {destino.saldo}"
            )

    def processar_em_ordem(self, transacoes: list[Transacao]) -> None:
        for transacao in sorted(transacoes, key=lambda t: t.datetime):
            self.transferir(transacao)