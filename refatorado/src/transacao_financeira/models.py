from dataclasses import dataclass
from decimal import Decimal

@dataclass
class Conta:
    numero: int
    saldo: Decimal
