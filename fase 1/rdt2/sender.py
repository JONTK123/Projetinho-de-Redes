import socket
import struct
import zlib
import random


RECEIVER_ADDR = ('127.0.0.1', 12000)
SENDER_ADDR = ('127.0.0.1', 12001)

TYPE_DATA = 0
TYPE_ACK = 1
TYPE_NAK = 2

HEADER_FMT = '!BI'
HEADER_SIZE = struct.calcsize(HEADER_FMT)

PROB_CORRUPCAO = 0.3


def make_data_pkt(data):
    checksum = zlib.crc32(data)
    header = struct.pack(HEADER_FMT, TYPE_DATA, checksum)
    return header + data


def corrupt_packet(packet, prob):
    if random.random() < prob:
        print("[Simulação] Corrompendo pacote...")
        idx = random.randint(0, len(packet) - 1)
        original_byte = packet[idx]
        bit_to_flip = 1 << random.randint(0, 7)
        corrupted_byte = original_byte ^ bit_to_flip
        pkt_list = list(packet)
        pkt_list[idx] = corrupted_byte
        return bytes(pkt_list)

    return packet


def unpack_feedback_pkt(packet):
    header = packet[:HEADER_SIZE]
    pkt_type, _ = struct.unpack(HEADER_FMT, header)
    return pkt_type


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(SENDER_ADDR)

    messages = [f"Mensagem {i}" for i in range(1, 11)]
    retransmissions = 0

    print(f"Remetente pronto para enviar {len(messages)} mensagens para {RECEIVER_ADDR}")
    print(f"Probabilidade de corrupção: {PROB_CORRUPCAO * 100}%\n")

    for msg in messages:
        print(f"--- Enviando: '{msg}' ---")

        payload = msg.encode('utf-8')
        sndpkt = make_data_pkt(payload)

        while True:
            pkt_to_send = corrupt_packet(sndpkt, PROB_CORRUPCAO)
            was_corrupted = pkt_to_send != sndpkt
            print(
                f"[RDT2][TX] enviar len={len(payload)} header={HEADER_SIZE} total={len(pkt_to_send)} "
                f"corrompido={'sim' if was_corrupted else 'nao'}"
            )

            sock.sendto(pkt_to_send, RECEIVER_ADDR)
            print("[RDT2][TX] enviado; aguardando ACK/NAK...")

            try:
                rcvpkt, addr = sock.recvfrom(1024)

                pkt_type = unpack_feedback_pkt(rcvpkt)
                tipo = {TYPE_ACK: 'ACK', TYPE_NAK: 'NAK'}.get(pkt_type, f'DESCONHECIDO({pkt_type})')
                print(f"[RDT2][RX] feedback tipo={tipo}")

                if pkt_type == TYPE_NAK:
                    print("[RDT2][RX] NAK recebido -> retransmitir mesmo pacote")
                    retransmissions += 1

                elif pkt_type == TYPE_ACK:
                    print("[RDT2][RX] ACK recebido -> avançar para próxima mensagem\n")
                    break

            except socket.timeout:
                print("Timeout! (Não deveria acontecer no RDT 2.0). Retransmitindo...")
                retransmissions += 1

    print("--- Transmissão Concluída ---")
    print(f"Total de retransmissões: {retransmissions}")
    sock.close()


if __name__ == "__main__":
    main()