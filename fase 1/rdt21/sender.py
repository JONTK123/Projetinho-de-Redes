import socket
import struct
import zlib
import random


RECEIVER_ADDR = ('127.0.0.1', 12100)
SENDER_ADDR = ('127.0.0.1', 12101)

TYPE_DATA = 0
TYPE_ACK = 1
TYPE_NAK = 2

HEADER_FMT = '!BBI'
HEADER_SIZE = struct.calcsize(HEADER_FMT)

DATA_CORRUPT_PROB = 0.2
ACK_CORRUPT_PROB = 0.2

def make_data_pkt(data: bytes, seqnum: int) -> bytes:
    checksum = zlib.crc32(data)
    header = struct.pack(HEADER_FMT, TYPE_DATA, seqnum, checksum)
    return header + data


def maybe_corrupt(packet: bytes, prob: float) -> bytes:
    if random.random() < prob and len(packet) > 0:
        print("[Simulação] Corrompendo pacote...")
        idx = random.randint(0, len(packet) - 1)
        b = packet[idx]
        bit = 1 << random.randint(0, 7)
        corrupted = bytes(packet[:idx] + bytes([b ^ bit]) + packet[idx + 1 :])
        return corrupted
    return packet


def unpack_feedback_pkt(packet: bytes):
    header = packet[:HEADER_SIZE]
    pkt_type, seqnum, _ = struct.unpack(HEADER_FMT, header)
    return pkt_type, seqnum, header


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(SENDER_ADDR)

    messages = [f"Mensagem {i}" for i in range(1, 11)]
    retransmissions = 0

    seqnum = 0

    print(f"[RDT2.1][Sender] Enviando {len(messages)} msgs para {RECEIVER_ADDR}")
    print(f"Corrupção: DATA={DATA_CORRUPT_PROB*100:.0f}% ACK={ACK_CORRUPT_PROB*100:.0f}%\n")

    for msg in messages:
        print(f"--- Enviando: '{msg}' seq={seqnum} ---")
        payload = msg.encode('utf-8')
        sndpkt = make_data_pkt(payload, seqnum)

        while True:
            pkt_to_send = maybe_corrupt(sndpkt, DATA_CORRUPT_PROB)
            was_corrupted = pkt_to_send != sndpkt
            print(
                f"[RDT2.1][TX] enviar seq={seqnum} len={len(payload)} header={HEADER_SIZE} total={len(pkt_to_send)} "
                f"corrompido={'sim' if was_corrupted else 'nao'}"
            )
            sock.sendto(pkt_to_send, RECEIVER_ADDR)
            print("[RDT2.1][TX] enviado; aguardando feedback...")

            try:
                rcvpkt, addr = sock.recvfrom(2048)
                rcv_corrupted = False
                maybe = maybe_corrupt(rcvpkt, ACK_CORRUPT_PROB)
                if maybe != rcvpkt:
                    rcv_corrupted = True
                    rcvpkt = maybe

                pkt_type, ack_seq, header = unpack_feedback_pkt(rcvpkt)
                tipo = {TYPE_ACK: 'ACK', TYPE_NAK: 'NAK'}.get(pkt_type, f'DESCONHECIDO({pkt_type})')
                print(f"[RDT2.1][RX]{'*' if rcv_corrupted else ' '} feedback tipo={tipo} ack_seq={ack_seq} esperado={seqnum}")

                if pkt_type in (TYPE_ACK, TYPE_NAK):
                    if pkt_type == TYPE_ACK and ack_seq == seqnum:
                        print(f"[RDT2.1][RX] ACK válido seq={seqnum} -> avançar\n")
                        seqnum = 1 - seqnum
                        break
                    elif pkt_type == TYPE_NAK:
                        print("[RDT2.1][RX] NAK recebido -> retransmitir mesmo pacote")
                        retransmissions += 1
                    else:
                        print("[RDT2.1][RX] ACK inesperado/corrompido -> retransmitir")
                        retransmissions += 1
                else:
                    print("[RDT2.1][RX] Feedback inválido -> retransmitir")
                    retransmissions += 1

            except socket.timeout:
                print("Timeout (não previsto no rdt2.1). Retransmitindo...")
                retransmissions += 1

    print("--- Transmissão Concluída (RDT2.1) ---")
    print(f"Total de retransmissões: {retransmissions}")
    sock.close()


if __name__ == "__main__":
    main()





