from decimal import Decimal

import pytest

from transacao_financeira.models import Conta


def test_criar_conta():
    conta = Conta(numero = 123, saldo = Decimal("100.50"))
    assert conta.numero == 123
    assert conta.saldo == Decimal("100.50")

def test_debito_saldo():
    conta = Conta(numero = 123, saldo = Decimal("100.50"))
    conta.saldo -= Decimal("50.25")
    assert conta.saldo == Decimal("50.25")

def test_credito_saldo():
    conta = Conta(numero = 123, saldo = Decimal("100.50"))
    conta.saldo += Decimal("25.75")
    assert conta.saldo == Decimal("126.25")

def test_numero_conta_grande():
    conta = Conta(numero = 2147483649, saldo = Decimal("0"))
    assert conta.numero == 2147483649