from decimal import Decimal

import pytest

from transacao_financeira.models import Conta
from transacao_financeira.repository import RepositorioContasMemoria


@pytest.fixture
def repositorio_contas() -> RepositorioContasMemoria:
    contas = [
        Conta(938485762, Decimal("180")),
        Conta(347586970, Decimal("1200")),
        Conta(2147483649, Decimal("0")),
        Conta(675869708, Decimal("4900")),
        Conta(238596054, Decimal("478")),
        Conta(573659065, Decimal("787")),
        Conta(210385733, Decimal("10")),
        Conta(674038564, Decimal("400")),
        Conta(563856300, Decimal("1200")),
    ]
    return RepositorioContasMemoria(contas)

def test_buscar_conta_existente(repositorio_contas):
    conta = repositorio_contas.buscar(938485762)
    assert conta.numero == 938485762
    assert conta.saldo == Decimal("180")

def test_buscar_outr_conta_conta_existente(repositorio_contas):
    conta = repositorio_contas.buscar(2147483649)
    assert conta.numero == 2147483649
    assert conta.saldo == Decimal("0")

def test_buscar_conta_inexistente(repositorio_contas):
    with pytest.raises(ValueError):
        repositorio_contas.buscar(999999999)

def test_listar_contas(repositorio_contas):
    contas = repositorio_contas.listar()
    assert len(contas) == 9
    numeros = [c.numero for c in contas]
    assert 938485762 in numeros
    assert 2147483649 in numeros
    assert 563856300 in numeros

def test_buscar_retorna_referencia_mutavel(repositorio_contas):
    conta = repositorio_contas.buscar(938485762)
    conta.saldo -= Decimal("50")
    conta2 = repositorio_contas.buscar(938485762)
    assert conta2.saldo == Decimal("130")  # Saldo atualizado na referência original