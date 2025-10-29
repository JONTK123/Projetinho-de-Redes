import socket
import struct
import zlib


RECEIVER_ADDR = ('127.0.0.1', 12100)
SENDER_ADDR = ('127.0.0.1', 12101)

TYPE_DATA = 0
TYPE_ACK = 1
TYPE_NAK = 2

HEADER_FMT = '!BBI'
HEADER_SIZE = struct.calcsize(HEADER_FMT)

def make_feedback_pkt(pkt_type: int, seqnum: int) -> bytes:
    data = b''
    checksum = zlib.crc32(data)
    header = struct.pack(HEADER_FMT, pkt_type, seqnum, checksum)
    return header + data


def verify_checksum(header: bytes, data: bytes) -> bool:
    _type, _seq, rcv_checksum = struct.unpack(HEADER_FMT, header)
    calc_checksum = zlib.crc32(data)
    return rcv_checksum == calc_checksum


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(RECEIVER_ADDR)

    print(f"[RDT2.1][Receiver] Ouvindo em {RECEIVER_ADDR}")

    expected_seq = 0
    received_messages = []

    while len(received_messages) < 10:
        try:
            packet, addr = sock.recvfrom(2048)
            if addr != SENDER_ADDR:
                print(f"Pacote de endereço inesperado {addr}. Ignorando.")
                continue

            header = packet[:HEADER_SIZE]
            data = packet[HEADER_SIZE:]

            pkt_type, seqnum, rcv_checksum = struct.unpack(HEADER_FMT, header)
            calc_checksum = zlib.crc32(data)
            print(
                f"[RDT2.1][RX] from={addr} type={pkt_type} seq={seqnum} expected={expected_seq} "
                f"len={len(data)} csum_rcv=0x{rcv_checksum:08X} csum_calc=0x{calc_checksum:08X}"
            )

            if pkt_type != TYPE_DATA:
                continue

            if verify_checksum(header, data):
                if seqnum == expected_seq:
                    msg = data.decode('utf-8')
                    print(f"[RDT2.1][RX] OK seq={seqnum} deliver='{msg}'")
                    received_messages.append(msg)

                    ack_pkt = make_feedback_pkt(TYPE_ACK, seqnum)
                    sock.sendto(ack_pkt, SENDER_ADDR)
                    print(f"[RDT2.1][RX->TX] ACK seq={seqnum}")

                    expected_seq = 1 - expected_seq
                else:
                    last_good_seq = 1 - expected_seq
                    print(f"[RDT2.1][RX] DUP seq={seqnum} expected={expected_seq} -> re-ACK({last_good_seq})")
                    dup_ack = make_feedback_pkt(TYPE_ACK, last_good_seq)
                    sock.sendto(dup_ack, SENDER_ADDR)
            else:
                print(f"[RDT2.1][RX] CORRUPTO seq={seqnum} expected={expected_seq} -> NAK({expected_seq})")
                nak_pkt = make_feedback_pkt(TYPE_NAK, expected_seq)
                sock.sendto(nak_pkt, SENDER_ADDR)

        except Exception as e:
            print(f"Erro ao receber pacote: {e}")

    print("\n--- Transmissão Concluída (RDT2.1) ---")
    print("Mensagens recebidas:")
    for i, msg in enumerate(received_messages):
        print(f"  {i + 1}: {msg}")

    sock.close()


if __name__ == "__main__":
    main()





