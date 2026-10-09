from typing import Protocol
from .models import Conta

class RepositorioContas(Protocol):
    def buscar(self, numero: int) -> Conta: ...
    def listar(self) -> list[Conta]: ...

class RepositorioContasMemoria:
    def __init__(self, contas: list[Conta]) -> None:
        self._contas: dict[int, Conta] = {c.numero: c for c in contas}

    def buscar(self, numero: int) -> Conta:
        if numero not in self._contas:
            raise ValueError(f"Conta {numero} não encontrada")
        return self._contas[numero]

    def listar(self) -> list[Conta]:
        return list(self._contas.values())
