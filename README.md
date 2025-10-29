# Projetinho-de-Redes

Implementações didáticas de transferência confiável sobre UDP: Fase 1 (RDT 2.0/2.1/3.0) e Fase 2 (GBN). Próxima etapa: TCP simplificado.

## Estrutura

- `rdt21/` e `rdt3/`: Fase 1 (rdt2.1: alternating bit; rdt3.0: timer + perdas)
- `fase2/gbn/`: Fase 2 (Go-Back-N com janela, ACK cumulativo, 1 timer)
- `utils/` (se aplicável) e `tests/` (futuros)

## Requisitos

- Python 3.12+
- (Opcional) Virtualenv: `source venv/bin/activate`

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
python3 /home/jontk123/GitHub/Projetinho-de-Redes/fase2/gbn/receiver.py
```

2) Remetente
```bash
python3 /home/jontk123/GitHub/Projetinho-de-Redes/fase2/gbn/sender.py
```

Parâmetros ajustáveis no sender (perdas, corrupção, atraso, timeout, tamanho da janela) estão no topo dos arquivos `sender.py` de cada fase.

## Próximas fases

- Selective Repeat (SR) para comparação com GBN
- TCP simplificado sobre UDP (handshake, seq por byte, ACK cumulativo, janela, timeout adaptativo)

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
