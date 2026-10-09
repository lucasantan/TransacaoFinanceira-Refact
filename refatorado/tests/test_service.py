from datetime import datetime
from decimal import Decimal
from threading import Thread

import pytest

from transacao_financeira.models import Conta
from transacao_financeira.repository import RepositorioContasMemoria
from transacao_financeira.service import ServicoTransacao, Transacao


def criar_servico(*contas: Conta) -> tuple[ServicoTransacao, list[Conta]]:
    lista = list(contas)
    return ServicoTransacao(RepositorioContasMemoria(lista)), lista


def tx(id: int, origem: int, destino: int, valor: str, segundos: int = 0) -> Transacao:
    return Transacao(
        correlation_id=id,
        datetime=datetime(2023, 1, 1, 0, 0, segundos),
        conta_origem=origem,
        conta_destino=destino,
        valor=Decimal(valor),
    )


class TestTransferenciaEfetivada:
    def test_debita_origem_e_credita_destino(self):
        servico, contas = criar_servico(Conta(1, Decimal("200")), Conta(2, Decimal("50")))
        servico.transferir(tx(1, 1, 2, "100"))
        assert contas[0].saldo == Decimal("100")
        assert contas[1].saldo == Decimal("150")

    def test_saldo_exato_e_efetivada(self):
        servico, contas = criar_servico(Conta(1, Decimal("100")), Conta(2, Decimal("0")))
        servico.transferir(tx(1, 1, 2, "100"))
        assert contas[0].saldo == Decimal("0")
        assert contas[1].saldo == Decimal("100")

    def test_stdout_contem_mensagem_de_sucesso(self, capsys):
        servico, _ = criar_servico(Conta(1, Decimal("200")), Conta(2, Decimal("50")))
        servico.transferir(tx(5, 1, 2, "100"))
        saida = capsys.readouterr().out
        assert "Transacao numero 5 foi efetivada com sucesso!" in saida
        assert "Conta Origem:100" in saida
        assert "Conta Destino: 150" in saida


class TestTransferenciaCancelada:
    def test_saldo_insuficiente_nao_altera_contas(self):
        servico, contas = criar_servico(Conta(1, Decimal("50")), Conta(2, Decimal("100")))
        servico.transferir(tx(1, 1, 2, "100"))
        assert contas[0].saldo == Decimal("50")
        assert contas[1].saldo == Decimal("100")

    def test_saldo_zero_e_cancelada(self):
        servico, contas = criar_servico(Conta(1, Decimal("0")), Conta(2, Decimal("100")))
        servico.transferir(tx(1, 1, 2, "1"))
        assert contas[0].saldo == Decimal("0")
        assert contas[1].saldo == Decimal("100")

    def test_stdout_contem_mensagem_de_cancelamento(self, capsys):
        servico, _ = criar_servico(Conta(1, Decimal("50")), Conta(2, Decimal("100")))
        servico.transferir(tx(3, 1, 2, "100"))
        saida = capsys.readouterr().out
        assert "Transacao numero 3 foi cancelada por falta de saldo" in saida


class TestOrdemCronologica:
    def test_tx2_depende_de_credito_feito_pela_tx1(self):
        """
        Conta 2 começa com 0. TX1 (14:15:00) credita 150 nela.
        TX2 (14:15:05) debita 149 da conta 2. Submetidas fora de ordem.
        Sem ordenação cronológica, TX2 seria cancelada incorretamente (Bug B3).
        """
        servico, contas = criar_servico(
            Conta(1, Decimal("180")),
            Conta(2, Decimal("0")),
            Conta(3, Decimal("10")),
        )
        tx1 = tx(1, 1, 2, "150", segundos=0)
        tx2 = tx(2, 2, 3, "149", segundos=5)

        # Submetidas em ordem invertida — processar_em_ordem deve corrigir
        servico.processar_em_ordem([tx2, tx1])

        assert contas[1].saldo == Decimal("1")    # 0 + 150 - 149
        assert contas[2].saldo == Decimal("159")  # 10 + 149

    def test_transacao_cancelada_corretamente_apos_debito_anterior(self):
        """
        TX1 debita conta 1 de 180 para 30. TX2 tenta debitar 44 — deve ser cancelada.
        """
        servico, contas = criar_servico(
            Conta(1, Decimal("180")),
            Conta(2, Decimal("0")),
        )
        tx1 = tx(1, 1, 2, "150", segundos=0)
        tx2 = tx(7, 1, 2, "44", segundos=10)

        servico.processar_em_ordem([tx1, tx2])

        assert contas[0].saldo == Decimal("30")   # só TX1 debitou
        assert contas[1].saldo == Decimal("150")  # só TX1 creditou


class TestThreadSafety:
    def test_duas_transferencias_concorrentes_nao_geram_saldo_negativo(self):
        """
        Duas threads debitam a mesma conta simultaneamente.
        Com o lock por conta, apenas uma deve passar quando o saldo não comporta as duas.
        Garante que o Bug B3 (race condition) não existe na versão Python.
        """
        servico, contas = criar_servico(
            Conta(1, Decimal("180")),
            Conta(2, Decimal("0")),
            Conta(3, Decimal("0")),
        )
        tx_a = tx(1, 1, 2, "150")
        tx_b = tx(2, 1, 3, "44")

        t1 = Thread(target=servico.transferir, args=(tx_a,))
        t2 = Thread(target=servico.transferir, args=(tx_b,))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert contas[0].saldo >= Decimal("0"), "Saldo nunca pode ficar negativo"
        total = contas[0].saldo + contas[1].saldo + contas[2].saldo
        assert total == Decimal("180"), "Soma dos saldos deve ser conservada"


class TestCenarioCompleto:
    def test_oito_transacoes_resultado_esperado(self, capsys):
        """
        Reproduz exatamente o cenário do main.py e valida saldos finais.
        Resultado esperado: TX1,2,3,5,6,8 efetivadas; TX4,7 canceladas.
        """
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
        repositorio = RepositorioContasMemoria(contas)
        servico = ServicoTransacao(repositorio)

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
        servico.processar_em_ordem(transacoes)

        mapa = {c.numero: c.saldo for c in contas}
        assert mapa[938485762] == Decimal("30")     # 180 - 150 (TX1); TX7 cancelada
        assert mapa[2147483649] == Decimal("1")     # 0 + 150 (TX1) - 149 (TX2)
        assert mapa[347586970] == Decimal("100")    # 1200 - 1100 (TX3)
        assert mapa[675869708] == Decimal("5050")   # 4900 + 150 (TX8); TX4 cancelada
        assert mapa[238596054] == Decimal("89")     # 478 + 1100 (TX3) - 1489 (TX5)
        assert mapa[573659065] == Decimal("588")    # 787 - 49 (TX6) - 150 (TX8)
        assert mapa[210385733] == Decimal("159")    # 10 + 149 (TX2); TX4 cancelada
        assert mapa[674038564] == Decimal("1889")   # 400 + 1489 (TX5)
        assert mapa[563856300] == Decimal("1249")   # 1200 + 49 (TX6)

        saida = capsys.readouterr().out
        assert saida.count("efetivada") == 6
        assert saida.count("cancelada") == 2