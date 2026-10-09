from datetime import datetime
from decimal import Decimal

from transacao_financeira.models import Conta
from transacao_financeira.repository import RepositorioContasMemoria
from transacao_financeira.service import ServicoTransacao, Transacao


def main() -> None:
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

    transacoes = [
        Transacao(1, datetime(2023, 9, 9, 14, 15, 0), 938485762, 2147483649, Decimal("150")),
        Transacao(2, datetime(2023, 9, 9, 14, 15, 5), 2147483649, 210385733, Decimal("149")),
        Transacao(3, datetime(2023, 9, 9, 14, 15, 29), 347586970, 238596054, Decimal("1100")),
        Transacao(4, datetime(2023, 9, 9, 14, 17, 0), 675869708, 210385733, Decimal("5300")),
        Transacao(5, datetime(2023, 9, 9, 14, 18, 0), 238596054, 674038564, Decimal("1489")),
        Transacao(6, datetime(2023, 9, 9, 14, 18, 20), 573659065, 563856300, Decimal("49")),
        Transacao(7, datetime(2023, 9, 9, 14, 19, 0), 938485762, 2147483649, Decimal("44")),
        Transacao(8, datetime(2023, 9, 9, 14, 19, 1), 573659065, 675869708, Decimal("150")),
    ]

    repositorio = RepositorioContasMemoria(contas)
    servico = ServicoTransacao(repositorio)
    servico.processar_em_ordem(transacoes)


if __name__ == "__main__":
    main()