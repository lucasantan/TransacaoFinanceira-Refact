# TransacaoFinanceira — Case de Refatoração

Este repositório documenta um exercício de refatoração: um simulador de transferências financeiras originalmente escrito em **C# .NET 5.0**, reescrito em **Python 3.12** com correção de bugs, aplicação de princípios SOLID e cobertura por testes unitários.

---

## Estrutura do repositório

```text
TransacaoFinanceira-Refact/
├── .gitignore
├── .vscode/
│   └── settings.json               # Configuração de análise Python no VS Code
├── README.md
│
├── original/                       # Projeto original em C# (.NET 5), mantido para referência
│   ├── Program.cs
│   ├── TransacaoFinanceira.csproj
│   └── README.md
│
└── refatorado/                     # Projeto refatorado em Python 3.12
    ├── pyproject.toml
    ├── src/transacao_financeira/
    │   ├── __init__.py
    │   ├── main.py                 # Ponto de entrada
    │   ├── models.py               # Domínio: Conta
    │   ├── repository.py           # Interface e repositório em memória
    │   └── service.py              # Lógica de transferência e thread-safety
    ├── tests/
    │   ├── __init__.py
    │   ├── test_models.py
    │   ├── test_repository.py
    │   └── test_service.py
```

Arquivos gerados durante builds e testes (como `obj/`, `__pycache__/` e `*.egg-info/`) são ignorados pelo Git e não fazem parte da estrutura-fonte.

---

## O que o programa faz

Processa 8 transferências financeiras entre contas com saldos iniciais definidos. A regra de negócio é simples: uma transferência é efetivada somente se o saldo da conta de origem for maior ou igual ao valor da transferência. As transações devem ser processadas na ordem cronológica do campo `datetime`, pois algumas dependem de créditos de transações anteriores.

**Resultado correto esperado:**

| TX | Origem | Destino | Valor | Decisão |
|----|--------|---------|-------|---------|
| 1 | 938485762 (saldo: 180) | 2147483649 | 150 | ✅ Efetivada |
| 2 | 2147483649 (saldo: 150, após TX1) | 210385733 | 149 | ✅ Efetivada |
| 3 | 347586970 (saldo: 1200) | 238596054 | 1100 | ✅ Efetivada |
| 4 | 675869708 (saldo: 4900) | 210385733 | 5300 | ❌ Cancelada — sem saldo |
| 5 | 238596054 (saldo: 1578, após TX3) | 674038564 | 1489 | ✅ Efetivada |
| 6 | 573659065 (saldo: 787) | 563856300 | 49 | ✅ Efetivada |
| 7 | 938485762 (saldo: 30, após TX1) | 2147483649 | 44 | ❌ Cancelada — sem saldo |
| 8 | 573659065 (saldo: 738, após TX6) | 675869708 | 150 | ✅ Efetivada |

---

## Bugs encontrados no código original (C#)

### Bug 1 — Estouro de inteiro (erro de compilação)
**Arquivo:** `original/Program.cs`

O número de conta `2147483649` excede o valor máximo de `int` (`2.147.483.647`). O compilador C# infere o literal como `long`, mas todos os parâmetros e propriedades que recebem números de conta eram declarados como `int`, causando erro de compilação `CS1503`.

**Impacto:** o projeto não compila.

**Correção na versão Python:** `int` em Python não tem limite de tamanho, o problema não existe na linguagem. Nenhuma adaptação foi necessária.

---

### Bug 2 — Índice inválido na string de formato (erro em tempo de execução)
**Arquivo:** `original/Program.cs`, linha 49

```csharp
// ERRADO — {3} referencia um 4º argumento que não existe
Console.WriteLine(
    "... Conta Origem:{1} | Conta Destino: {3}",
    correlation_id,             // {0}
    conta_saldo_origem.saldo,   // {1}
    conta_saldo_destino.saldo   // {2} — passado como argumento, mas nunca referenciado
);
```

O saldo de destino era o terceiro argumento (índice `{2}`), mas a string usava `{3}`. Isso lançava `System.FormatException` em toda transferência bem-sucedida, travando o programa.

**Correção na versão Python:** uso de f-strings elimina índices por completo:
```python
print(
    f"Transacao numero {transacao.correlation_id} foi efetivada com sucesso! "
    f"Novos saldos: Conta Origem:{origem.saldo} | Conta Destino: {destino.saldo}"
)
```

---

### Bug 3 — Race condition: transações sem ordem e sem sincronização (bug de lógica)
**Arquivo:** `original/Program.cs`, linhas 26-50

Este é o bug mais crítico e a causa-raiz dos dois comportamentos anômalos descritos nos requisitos:

**Causa:** o uso de `Parallel.ForEach` sem nenhum mecanismo de sincronização (`lock`) e sem respeitar a ordem cronológica das transações.

**Cenário "efetivada sem saldo":**
```
Thread A (TX1, conta 938485762, valor 150):   Thread B (TX7, conta 938485762, valor 44):
  lê saldo → 180                                lê saldo → 180  ← mesmo objeto, ao mesmo tempo
  180 >= 150 → PASSA                            180 >= 44  → PASSA  ← ambas aprovadas juntas
  saldo -= 150 → 30                             saldo -= 44 → -14  ← SALDO NEGATIVO
  → "efetivada"                                 → "efetivada"
```

**Cenário "cancelada com saldo positivo":**
A TX2 transfere da conta `2147483649`, que começa com saldo 0. Ela só deveria ser executada após a TX1 creditar 150 nessa conta. Com `Parallel.ForEach`, TX2 pode rodar antes de TX1 — vê saldo 0, é cancelada incorretamente, mesmo com saldo suficiente no momento correto.

**Correção na versão Python:**
1. `processar_em_ordem` ordena todas as transações pelo `datetime` antes de executar.
2. Um `threading.Lock` por conta-origem garante que o ciclo verificar → debitar é atômico — nenhuma outra thread pode ler o saldo entre a verificação e o débito da mesma conta.

```python
def transferir(self, transacao: Transacao) -> None:
    lock = self._obter_lock(transacao.conta_origem)
    with lock:                                          # atomicidade garantida
        origem = self._repositorio.buscar(transacao.conta_origem)
        if origem.saldo < transacao.valor:
            print(f"Transacao numero {transacao.correlation_id} foi cancelada por falta de saldo")
            return
        destino = self._repositorio.buscar(transacao.conta_destino)
        origem.saldo -= transacao.valor
        destino.saldo += transacao.valor
```

---

### Bug 4 — `atualizar()` nunca chamado (falha de design)
**Arquivo:** `original/Program.cs`

O método `atualizar()` foi projetado para persistir atualizações de saldo, mas nunca era chamado em `transferir()`. O código funcionava por acidente: `getSaldo` retornava a referência direta do objeto, então modificar `.saldo` alterava o estado em memória implicitamente — um efeito colateral frágil que quebraria se `getSaldo` fosse alterado para retornar cópias.

**Correção na versão Python:** o repositório devolve a referência do objeto `Conta` de forma explícita e documentada. O serviço muta diretamente, sem depender de comportamento implícito.

---

### Bug 5 — Código morto: `Dictionary<int, decimal> SALDOS`
**Arquivo:** `original/Program.cs`

Um dicionário `SALDOS` era declarado, instanciado e populado com uma única entrada, mas nunca lido. Código sem utilidade que confunde a leitura.

**Correção na versão Python:** removido completamente. O `RepositorioContasMemoria` usa apenas um `dict[int, Conta]` claro e bem definido.

---

## Decisões de arquitetura na versão Python

### SOLID aplicado

| Princípio | Aplicação |
|-----------|-----------|
| **S**ingle Responsibility | `Conta` só modela o domínio; `RepositorioContasMemoria` só gerencia persistência; `ServicoTransacao` só contém a regra de negócio |
| **O**pen/Closed | Adicionar uma nova implementação de repositório (ex: banco de dados) não exige alterar `ServicoTransacao` |
| **L**iskov Substitution | `RepositorioContasMemoria` implementa `RepositorioContas` (Protocol) e pode ser substituída sem quebrar o serviço |
| **I**nterface Segregation | `RepositorioContas` expõe apenas `buscar` e `listar` — sem métodos desnecessários |
| **D**ependency Inversion | `ServicoTransacao` recebe um `RepositorioContas` via construtor — nunca instancia o repositório diretamente |

### Repository Pattern
A interface `RepositorioContas` (definida como `Protocol` do Python) desacopla o serviço da implementação de persistência. Isso permite trocar o armazenamento em memória por qualquer outro (banco relacional, NoSQL) sem tocar no `ServicoTransacao`.

### `decimal.Decimal` para valores monetários
`float` em Python (e em qualquer linguagem) tem imprecisão de ponto flutuante que é inaceitável para dinheiro. `Decimal` garante aritmética exata:
```python
# float (ERRADO para dinheiro)
0.1 + 0.2 == 0.30000000000000004

# Decimal (CORRETO)
Decimal("0.1") + Decimal("0.2") == Decimal("0.3")
```

### `dataclass` para `Conta` e `Transacao`
Gera automaticamente `__init__`, `__repr__` e `__eq__`, sem boilerplate. A mutabilidade de `Conta` é intencional: o repositório mantém as referências e o serviço atualiza os saldos diretamente.

---

## Como executar

### Pré-requisitos
- Python 3.12+

### Instalação

```bash
cd refatorado
pip install -e ".[dev]"
```

### Executar o programa

```bash
cd refatorado/src
python -m transacao_financeira.main
```

**Saída esperada:**
```
Transacao numero 1 efetivada com sucesso! Novos saldos: Conta Origem: conta: 938485762, saldo: 30 | Conta Destino: conta: 2147483649, saldo: 150
Transacao numero 2 efetivada com sucesso! Novos saldos: Conta Origem: conta: 2147483649, saldo: 1 | Conta Destino: conta: 210385733, saldo: 159
Transacao numero 3 efetivada com sucesso! Novos saldos: Conta Origem: conta: 347586970, saldo: 100 | Conta Destino: conta: 238596054, saldo: 1578
Transacao numero 4 falhou: saldo insuficiente na conta 675869708
Transacao numero 5 efetivada com sucesso! Novos saldos: Conta Origem: conta: 238596054, saldo: 89 | Conta Destino: conta: 674038564, saldo: 1889
Transacao numero 6 efetivada com sucesso! Novos saldos: Conta Origem: conta: 573659065, saldo: 738 | Conta Destino: conta: 563856300, saldo: 1249
Transacao numero 7 falhou: saldo insuficiente na conta 938485762
Transacao numero 8 efetivada com sucesso! Novos saldos: Conta Origem: conta: 573659065, saldo: 588 | Conta Destino: conta: 675869708, saldo: 5050
```

### Executar os testes

```bash
cd refatorado
pytest -v
```

```bash
# Com relatório de cobertura
pytest --cov=transacao_financeira --cov-report=term-missing
```

---

## Dependências

| Dependência | Versão | Uso |
|-------------|--------|-----|
| Python | ≥ 3.12 | Runtime |
| pytest | ≥ 8.0 | Execução dos testes |
| pytest-cov | ≥ 5.0 | Relatório de cobertura |

Sem dependências de runtime além da stdlib (`decimal`, `threading`, `datetime`, `dataclasses`).

---

## Testes unitários — cobertura

| Arquivo | O que é testado |
|---------|-----------------|
| `test_models.py` | Criação de `Conta`, débito, crédito, número de conta grande (regressão Bug B1) |
| `test_repository.py` | Busca por conta existente e inexistente, listagem, mutabilidade da referência |
| `test_service.py` | Transferência efetivada, cancelada, saldo exato, saída stdout, ordem cronológica (regressão Bug B3), thread-safety, cenário completo com os 8 dados reais |