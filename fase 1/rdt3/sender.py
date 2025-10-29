import socket
import struct
import zlib
import random
import time


RECEIVER_ADDR = ('127.0.0.1', 12200)
SENDER_ADDR = ('127.0.0.1', 12201)

TYPE_DATA = 0
TYPE_ACK = 1
TYPE_NAK = 2

HEADER_FMT = '!BBI'
HEADER_SIZE = struct.calcsize(HEADER_FMT)

DATA_LOSS_PROB = 0.15
ACK_LOSS_PROB = 0.15
DATA_CORRUPT_PROB = 0.15
ACK_CORRUPT_PROB = 0.15
DELAY_MIN_S = 0.05
DELAY_MAX_S = 0.50

TIMEOUT_S = 2.0

def make_data_pkt(data: bytes, seqnum: int) -> bytes:
    checksum = zlib.crc32(data)
    header = struct.pack(HEADER_FMT, TYPE_DATA, seqnum, checksum)
    return header + data


def maybe_corrupt(packet: bytes, prob: float) -> bytes:
    if random.random() < prob and len(packet) > 0:
        idx = random.randint(0, len(packet) - 1)
        b = packet[idx]
        bit = 1 << random.randint(0, 7)
        return bytes(packet[:idx] + bytes([b ^ bit]) + packet[idx + 1 :])
    return packet


def unpack_feedback_pkt(packet: bytes):
    header = packet[:HEADER_SIZE]
    pkt_type, seqnum, _ = struct.unpack(HEADER_FMT, header)
    return pkt_type, seqnum


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(SENDER_ADDR)
    sock.settimeout(TIMEOUT_S)

    messages = [f"Mensagem {i}" for i in range(1, 11)]
    retransmissions = 0
    seqnum = 0

    print(f"[RDT3.0][Sender] Enviando {len(messages)} msgs para {RECEIVER_ADDR}")
    print(
        f"loss: DATA={int(DATA_LOSS_PROB*100)}% ACK={int(ACK_LOSS_PROB*100)}% | "
        f"corrupção: DATA={int(DATA_CORRUPT_PROB*100)}% ACK={int(ACK_CORRUPT_PROB*100)}% | "
        f"delay={int(DELAY_MIN_S*1000)}-{int(DELAY_MAX_S*1000)}ms | timeout={TIMEOUT_S:.1f}s\n"
    )

    for msg in messages:
        payload = msg.encode('utf-8')
        sndpkt = make_data_pkt(payload, seqnum)

        print(f"--- Enviando: '{msg}' seq={seqnum} ---")

        while True:
            time.sleep(random.uniform(DELAY_MIN_S, DELAY_MAX_S))

            if random.random() < DATA_LOSS_PROB:
                print(f"[RDT3.0][TX] DROP DATA seq={seqnum} (perda simulada)")
            else:
                pkt_to_send = maybe_corrupt(sndpkt, DATA_CORRUPT_PROB)
                was_corrupted = pkt_to_send != sndpkt
                print(
                    f"[RDT3.0][TX] enviar seq={seqnum} len={len(payload)} header={HEADER_SIZE} total={len(pkt_to_send)} "
                    f"corrompido={'sim' if was_corrupted else 'nao'}"
                )
                sock.sendto(pkt_to_send, RECEIVER_ADDR)

            print("[RDT3.0][TX] aguardando ACK...")

            try:
                rcvpkt, addr = sock.recvfrom(4096)

                if random.random() < ACK_LOSS_PROB:
                    print("[RDT3.0][RX] DROP ACK (perda simulada no sender)")
                    raise socket.timeout

                maybe = maybe_corrupt(rcvpkt, ACK_CORRUPT_PROB)
                corrupted_ack = maybe != rcvpkt
                rcvpkt = maybe

                pkt_type, ack_seq = unpack_feedback_pkt(rcvpkt)
                tipo = {TYPE_ACK: 'ACK', TYPE_NAK: 'NAK'}.get(pkt_type, f'UNK({pkt_type})')
                print(f"[RDT3.0][RX]{'*' if corrupted_ack else ' '} feedback {tipo} ack_seq={ack_seq} esperado={seqnum}")

                if pkt_type == TYPE_ACK and ack_seq == seqnum:
                    print(f"[RDT3.0][RX] ACK válido seq={seqnum} -> avançar\n")
                    seqnum = 1 - seqnum
                    break
                elif pkt_type == TYPE_NAK:
                    print("[RDT3.0][RX] NAK recebido -> retransmitir")
                    retransmissions += 1
                else:
                    print("[RDT3.0][RX] feedback inválido/inesperado -> retransmitir")
                    retransmissions += 1

            except socket.timeout:
                print("[RDT3.0][TX] TIMEOUT -> retransmitir")
                retransmissions += 1

    print("--- Transmissão Concluída (RDT3.0) ---")
    print(f"Total de retransmissões: {retransmissions}")
    sock.close()


if __name__ == "__main__":
    main()


