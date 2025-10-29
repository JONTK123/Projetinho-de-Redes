import socket
import struct
import zlib


RECEIVER_ADDR = ('127.0.0.1', 12300)
SENDER_ADDR = ('127.0.0.1', 12301)

TYPE_DATA = 0
TYPE_ACK = 1

HEADER_FMT = '!BII'
HEADER_SIZE = struct.calcsize(HEADER_FMT)


def make_ack(ack_num: int) -> bytes:
    data = b''
    checksum = zlib.crc32(data)
    header = struct.pack(HEADER_FMT, TYPE_ACK, ack_num, checksum)
    return header


def verify_checksum(header: bytes, data: bytes) -> bool:
    _type, _seq, rcv_checksum = struct.unpack(HEADER_FMT, header)
    calc = zlib.crc32(data)
    return rcv_checksum == calc


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(RECEIVER_ADDR)

    print(f"RECEIVER (GBN): Listening on {RECEIVER_ADDR}.\n")

    expected_seq = 1  # começa em 1 para facilitar ACK cumulativo inicial
    received = []

    while len(received) < 10:
        try:
            packet, addr = sock.recvfrom(8192)
            if addr != SENDER_ADDR:
                continue

            header = packet[:HEADER_SIZE]
            data = packet[HEADER_SIZE:]
            pkt_type, seqnum, rcv_checksum = struct.unpack(HEADER_FMT, header)

            if pkt_type != TYPE_DATA:
                continue

            calc = zlib.crc32(data)

            if verify_checksum(header, data) and seqnum == expected_seq:
                msg = data.decode('utf-8')
                print(f"RECEIVER (GBN): Received DATA seq={seqnum} (checksum OK). Delivering to app and sending ACK {seqnum}.\n")
                received.append(msg)
                ack = make_ack(seqnum)
                sock.sendto(ack, SENDER_ADDR)
                expected_seq += 1
            else:
                # fora de ordem ou corrompido: reenvia ACK do último em ordem (expected-1)
                last_in_order = expected_seq - 1
                ack = make_ack(last_in_order)
                sock.sendto(ack, SENDER_ADDR)
                print(f"RECEIVER (GBN): Out-of-order or corrupt segment (got seq={seqnum}, expected={expected_seq}). Re-sending cumulative ACK {last_in_order}.\n")

        except Exception as e:
            print(f"[GBN][RX] erro: {e}")

    print("\nRECEIVER (GBN): Completed. All messages received in order:")
    for i, m in enumerate(received, 1):
        print(f"  {i}: {m}")
    sock.close()


if __name__ == "__main__":
    main()


