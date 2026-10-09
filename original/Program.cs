using System;
using System.Collections.Generic;
using System.Threading.Tasks;


//Obs: Voce é livre para implementar na linguagem de sua preferência, desde que respeite as funcionalidades e saídas existentes, além de aplicar os conceitos solicitados.

namespace TransacaoFinanceira
{
    class Program
    {

        static void Main(string[] args)
        {
            var TRANSACOES = new[] { new {correlation_id= 1,datetime="09/09/2023 14:15:00", conta_origem= 938485762, conta_destino= 2147483649, VALOR= 150},
                                     new {correlation_id= 2,datetime="09/09/2023 14:15:05", conta_origem= 2147483649, conta_destino= 210385733, VALOR= 149},
                                     new {correlation_id= 3,datetime="09/09/2023 14:15:29", conta_origem= 347586970, conta_destino= 238596054, VALOR= 1100},
                                     new {correlation_id= 4,datetime="09/09/2023 14:17:00", conta_origem= 675869708, conta_destino= 210385733, VALOR= 5300},
                                     new {correlation_id= 5,datetime="09/09/2023 14:18:00", conta_origem= 238596054, conta_destino= 674038564, VALOR= 1489},
                                     new {correlation_id= 6,datetime="09/09/2023 14:18:20", conta_origem= 573659065, conta_destino= 563856300, VALOR= 49},
                                     new {correlation_id= 7,datetime="09/09/2023 14:19:00", conta_origem= 938485762, conta_destino= 2147483649, VALOR= 44},
                                     new {correlation_id= 8,datetime="09/09/2023 14:19:01", conta_origem= 573659065, conta_destino= 675869708, VALOR= 150},

            };
            executarTransacaoFinanceira executor = new executarTransacaoFinanceira();
            Parallel.ForEach(TRANSACOES, item =>
            {
                executor.transferir(item.correlation_id, item.conta_origem, item.conta_destino, item.VALOR);
            });

        }
    }

    class executarTransacaoFinanceira: acessoDados
    {
        public void transferir(int correlation_id, int conta_origem, int conta_destino, decimal valor)
        {
            contas_saldo conta_saldo_origem = getSaldo<contas_saldo>(conta_origem) ;
            if (conta_saldo_origem.saldo < valor)
            {
                Console.WriteLine("Transacao numero {0 } foi cancelada por falta de saldo", correlation_id);

            }
            else
            {
                contas_saldo conta_saldo_destino = getSaldo<contas_saldo>(conta_destino);
                conta_saldo_origem.saldo -= valor;
                conta_saldo_destino.saldo += valor;
                Console.WriteLine("Transacao numero {0} foi efetivada com sucesso! Novos saldos: Conta Origem:{1} | Conta Destino: {3}", correlation_id, conta_saldo_origem.saldo, conta_saldo_destino.saldo);
            }
        }
    }
    class contas_saldo
    {
        public contas_saldo(int conta, decimal valor)
        {
            this.conta = conta;
            this.saldo = valor;
        }
        public int conta { get; set; }
        public decimal saldo { get; set; }
    }
    class acessoDados
    {
        Dictionary<int, decimal> SALDOS { get; set; }
        private List<contas_saldo> TABELA_SALDOS;
        public acessoDados()
        {
            TABELA_SALDOS = new List<contas_saldo>();
            TABELA_SALDOS.Add(new contas_saldo(938485762, 180));
            TABELA_SALDOS.Add(new contas_saldo(347586970, 1200));
            TABELA_SALDOS.Add(new contas_saldo(2147483649, 0));
            TABELA_SALDOS.Add(new contas_saldo(675869708, 4900));
            TABELA_SALDOS.Add(new contas_saldo(238596054, 478));
            TABELA_SALDOS.Add(new contas_saldo(573659065, 787));
            TABELA_SALDOS.Add(new contas_saldo(210385733, 10));
            TABELA_SALDOS.Add(new contas_saldo(674038564, 400));
            TABELA_SALDOS.Add(new contas_saldo(563856300, 1200));


            SALDOS = new Dictionary<int, decimal>();
            this.SALDOS.Add(938485762, 180);
           
        }
        public T getSaldo<T>(int id)
        {          
            return (T)Convert.ChangeType(TABELA_SALDOS.Find(x => x.conta == id), typeof(T));
        }
        public bool atualizar<T>(T  dado)
        {
            try
            {
                contas_saldo item = (dado as contas_saldo);
                TABELA_SALDOS.RemoveAll(x => x.conta == item.conta);
                TABELA_SALDOS.Add(dado as contas_saldo);
                return true;
            }
            catch (Exception e)
            {
                Console.WriteLine(e.Message);
                return false;
            }
            
        }

    }
}
