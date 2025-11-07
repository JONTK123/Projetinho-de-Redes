# Projetinho-de-Redes

Implementações didáticas de transferência confiável sobre UDP: **TODAS AS 3 FASES COMPLETAS E TESTADAS** ✅

- **Fase 1**: RDT 2.0, 2.1, 3.0 (transferência confiável com ACK/NAK, sequência, timer)
- **Fase 2**: Go-Back-N (pipelining com janela deslizante)
- **Fase 3**: TCP simplificado sobre UDP (handshake, controle de fluxo, timeout adaptativo)

## Estrutura do Projeto

```
Projetinho-de-Redes/
├── fase 1/              # Fase 1: Protocolos RDT
│   ├── rdt2/           # RDT 2.0 (ACK/NAK)
│   ├── rdt21/          # RDT 2.1 (números de sequência)
│   └── rdt3/           # RDT 3.0 (timer + perda)
├── fase2/               # Fase 2: Pipelining
│   └── gbn/            # Go-Back-N
├── tcp/                 # Fase 3: TCP sobre UDP
│   ├── simple_tcp_full.py  # Implementação completa do TCP
│   ├── client.py           # Cliente de teste
│   └── server.py           # Servidor de teste
├── tests/               # Suite de testes automatizados
│   └── test_all_phases.py
├── TEST_RESULTS.md      # Resultados detalhados dos testes
└── README.md
```

## Requisitos

- Python 3.12+
- (Opcional) Virtualenv: `source venv/bin/activate`

## Status dos Testes ✅

**TODAS AS FASES TESTADAS E APROVADAS - 100% DE SUCESSO**

Para ver os resultados detalhados dos testes, consulte [TEST_RESULTS.md](TEST_RESULTS.md)

```bash
# Executar todos os testes automatizados
python3 tests/test_all_phases.py
```

**Resumo dos Resultados**:
- ✅ Fase 1 - RDT 2.0: PASSOU (detecção de erros com ACK/NAK)
- ✅ Fase 1 - RDT 2.1: PASSOU (números de sequência alternantes)
- ✅ Fase 1 - RDT 3.0: PASSOU (timer e recuperação de perdas)
- ✅ Fase 2 - Go-Back-N: PASSOU (pipelining com janela N=5)
- ✅ Fase 3 - TCP sobre UDP: PASSOU (handshake, transferência, close)

Taxa de Sucesso: **5/5 testes (100%)**

## Como rodar (exemplos)

Fase 1 — rdt2.1

1) Receptor
```bash
python3 /home/jontk123/GitHub/Projetinho-de-Redes/rdt21/receiver.py
```

2) Remetente
```bash
python3 /home/jontk123/GitHub/Projetinho-de-Redes/rdt21/sender.py
```

Fase 1 — rdt3.0

1) Receptor
```bash
python3 /home/jontk123/GitHub/Projetinho-de-Redes/rdt3/receiver.py
```

2) Remetente
```bash
python3 /home/jontk123/GitHub/Projetinho-de-Redes/rdt3/sender.py
```

Fase 2 — Go-Back-N (GBN)

1) Receptor
```bash
python3 "fase2/gbn/receiver.py"
```

2) Remetente
```bash
python3 "fase2/gbn/sender.py"
```

Fase 3 — TCP Simplificado sobre UDP

1) Servidor
```bash
python3 tcp/server.py
```

2) Cliente (em outro terminal)
```bash
python3 tcp/client.py
```

Parâmetros ajustáveis no sender (perdas, corrupção, atraso, timeout, tamanho da janela) estão no topo dos arquivos `sender.py` de cada fase.

## O que foi implementado

### Fase 3 - TCP sobre UDP (COMPLETO)

A implementação TCP inclui todas as funcionalidades exigidas:

✅ **Estabelecimento de Conexão (Three-Way Handshake)**
- Cliente envia SYN
- Servidor responde SYN-ACK
- Cliente envia ACK final
- Conexão estabelecida

✅ **Estrutura do Segmento TCP**
- Cabeçalho de 20 bytes (compatível com TCP real)
- Campos: Source Port, Dest Port, Seq Number, ACK Number, Flags, Window Size
- Flags implementadas: SYN, ACK, FIN

✅ **Números de Sequência e ACKs**
- Números de sequência baseados em bytes (não em segmentos)
- ACKs cumulativos (próximo byte esperado)
- Espaço de 32 bits para números de sequência

✅ **Gerenciamento de Buffers**
- Buffer de envio: armazena dados até serem confirmados
- Buffer de recepção: armazena dados recebidos até aplicação ler

✅ **Timer e Retransmissão**
- Timeout adaptativo baseado em RTT
- Fórmulas implementadas:
  - `EstimatedRTT = 0.875 * EstimatedRTT + 0.125 * SampleRTT`
  - `DevRTT = 0.75 * DevRTT + 0.25 * |SampleRTT - EstimatedRTT|`
  - `TimeoutInterval = EstimatedRTT + 4 * DevRTT`

✅ **Controle de Fluxo**
- Campo Window Size indica espaço livre no buffer
- Remetente respeita janela anunciada
- `LastByteSent - LastByteAcked ≤ rwnd`

✅ **Encerramento de Conexão**
- FIN para iniciar encerramento
- ACK para confirmar
- Handshake de encerramento completo

✅ **Simulação de Rede Não Confiável**
- Taxa de perda configurável (padrão: 20%)
- Recuperação automática via retransmissão

**Desempenho medido**:
- Throughput: ~189 Mbps (em localhost)
- MSS: 1024 bytes
- Window size: 4096 bytes
- Transferência de 10KB testada com sucesso

## Conceitos importantes (resumo didático)

- Buffer do receptor
  - Conceito: espaço para guardar dados recebidos que ainda não foram entregues/confirmados.
  - Em GBN “puro”: o receptor não bufferiza fora de ordem; mantém apenas o último em ordem e reenvia ACK cumulativo. O buffer efetivo é o da aplicação/SO (socket) para dados válidos.
  - Em SR (Selective Repeat): o receptor mantém um buffer de recepção para armazenar pacotes fora de ordem até o faltante chegar.

- Relação com banda (largura de banda) e RTT
  - BDP (Bandwidth-Delay Product) ≈ banda × RTT → “quantidade de dados no fio”.
  - Janela ideal em bytes ≈ BDP. Janela muito menor que o BDP subutiliza o enlace; muito maior pode gerar filas, perdas e mais retransmissões.
  - Com banda baixa (ou RTT alto), o BDP é menor → uma janela menor (N) costuma ser suficiente e mais estável.

- Prática no GBN deste projeto
  - `WINDOW_SIZE` controla quantos segmentos sem ACK ficam em voo (pendentes) simultaneamente.
    - Muitos timeouts/perdas → reduza `WINDOW_SIZE`.
    - Rede folgada/RTT não é gargalo → aumente `WINDOW_SIZE` para maior throughput.
  - Ajuste `TIMEOUT_S`: RTT maior → `TIMEOUT_S` um pouco maior; RTT menor → `TIMEOUT_S` menor.

- Regras rápidas
  - GBN: receptor não guarda fora de ordem (reenvia ACK cumulativo). SR: guarda fora de ordem.
  - Janela em voo (bytes) ≈ min(BDP, buffer do receptor). Em segmentos: N ≈ BDP / tamanho_segmento.
  - Largura de banda baixa → prefira janela menor para evitar fila e perdas.

- Janela e sequências no GBN
  - “No máximo N” significa até N segmentos pendentes sem ACK. Ao chegar um ACK cumulativo, a janela desliza e libera espaço para novos envios.
  - Ex.: N=5. Se `base=1`, janela cobre [1..5]. Chega ACK=3 → confirma 1..3, `base=4`, janela vira [4..8].

- Tamanho da janela escolhido nos testes
  - Usamos `WINDOW_SIZE = 5` por padrão. É configurável em `fase2/gbn/sender.py`.
  - Trade-off: janela maior usa melhor o RTT (maior throughput), mas pode estourar buffers e, no GBN, aumenta o custo de timeout (retransmite toda a janela pendente).

- Números de sequência
  - Fase 1 (rdt2.0/2.1/3.0): “alternating bit” (1 bit) → 0/1.
  - Fase 2 (GBN): inteiro de 32 bits (`HEADER_FMT = '!BII'`, campo `I`) → 0 a 2^32−1.
  - Observações: 32 bits permitem numerar bilhões de segmentos antes de wrap-around; GBN usa ACK cumulativo ACK(n) confirmando todos até n. Em janelas circulares, regra clássica para evitar ambiguidade: N < 2^(k−1) (k = bits do seq).

- RTT (Round-Trip Time)
  - Geral, não é específico de HTTP. É o tempo ida‑e‑volta entre enviar um segmento/pacote e receber a resposta/ACK.
  - Transporte: TCP estima RTT para definir timeout; rdt3.0 usa timeout fixo (conceito análogo). Aplicação: HTTP sente impacto de RTT; ping mede RTT.

## Fase 1 — notas rápidas

- rdt3.0 criado em `rdt3/`:
  - `rdt3/receiver.py`: mesma lógica do rdt2.1 (seq 0/1, ACK do último válido, NAK em corrompido), com logs claros.
  - `rdt3/sender.py`: alternating bit com timer (timeout), simulação de perda/corrupção/atraso; retransmite em NAK, feedback inválido ou timeout. Logs mostram seq, tamanhos, perdas e decisões.

- Exemplo de decisão no receiver (rdt2.1/rdt3.0):
  - OK seq=0 → envia ACK(0), `expected_seq` vira 1.
  - Duplicado seq=0 → reenvia ACK(0), `expected_seq` continua 1.
  - Próximo DATA seq=1 corrompido → “Pacote CORROMPIDO. Enviando NAK(1)”.

- “Feedback inválido” (rdt2.1/rdt3.0, no sender)
  - Tipo inválido: cabeçalho corrompido (não é ACK/NAK) → trata como inválido e retransmite.
  - ACK inesperado: `ack_seq` não bate com o `seqnum` atual → trata como corrompido/inesperado e retransmite.
  - Causas: corrupção do cabeçalho do feedback, truncamento/ruído, corrupção simulada (`maybe_corrupt` aplicada ao ACK no sender).

- Observação sobre corrupção
  - O protocolo não “corrige” bits; detecta (checksum/seq) e resolve por retransmissão. Na nova tentativa, se chegar íntegro, o ciclo fecha com ACK válido.
