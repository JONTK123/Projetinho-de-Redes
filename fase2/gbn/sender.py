import socket
import struct
import zlib
import random
import time


RECEIVER_ADDR = ('127.0.0.1', 12300)
SENDER_ADDR = ('127.0.0.1', 12301)

TYPE_DATA = 0
TYPE_ACK = 1

HEADER_FMT = '!BII'
HEADER_SIZE = struct.calcsize(HEADER_FMT)

WINDOW_SIZE = 5
TIMEOUT_S = 1.0

DATA_LOSS_PROB = 0.10
ACK_LOSS_PROB = 0.10
DATA_CORRUPT_PROB = 0.10
ACK_CORRUPT_PROB = 0.10
DELAY_MIN_S = 0.02
DELAY_MAX_S = 0.20


def make_data(seqnum: int, data: bytes) -> bytes:
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


def unpack_ack(packet: bytes):
    header = packet[:HEADER_SIZE]
    pkt_type, ack_num, _ = struct.unpack(HEADER_FMT, header)
    return pkt_type, ack_num


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(SENDER_ADDR)
    sock.settimeout(0.1)

    messages = [f"Mensagem {i}".encode('utf-8') for i in range(1, 11)]
    total = len(messages)

    base = 1
    nextseqnum = 1
    buffer = {}
    sent_time = None
    retransmissions = 0

    print(f"SENDER (GBN): Starting to send {total} messages to {RECEIVER_ADDR} with window size N={WINDOW_SIZE}.\n")

    while base <= total:
        # Envia enquanto houver espaço na janela
        while nextseqnum < base + WINDOW_SIZE and nextseqnum <= total:
            data = messages[nextseqnum - 1]
            pkt = make_data(nextseqnum, data)

            time.sleep(random.uniform(DELAY_MIN_S, DELAY_MAX_S))
            if random.random() < DATA_LOSS_PROB:
                print(f"SENDER (GBN): Simulated DROP of DATA segment seq={nextseqnum}.\n")
            else:
                pkt_to_send = maybe_corrupt(pkt, DATA_CORRUPT_PROB)
                was_corrupted = pkt_to_send != pkt
                corruption_note = " (with 1-bit corruption)" if was_corrupted else ""
                print(
                    f"SENDER (GBN): Sending DATA seq={nextseqnum}{corruption_note}. "
                    f"Current window = [{base}..{base+WINDOW_SIZE-1}]."
                )
                sock.sendto(pkt_to_send, RECEIVER_ADDR)
                print()

            buffer[nextseqnum] = pkt
            if base == nextseqnum:
                sent_time = time.time()
            nextseqnum += 1

        # Tenta receber ACK
        try:
            rcv, addr = sock.recvfrom(8192)

            if random.random() < ACK_LOSS_PROB:
                print("SENDER (GBN): Simulated DROP of incoming ACK. Will behave as if no ACK arrived.\n")
                raise socket.timeout

            rcv = maybe_corrupt(rcv, ACK_CORRUPT_PROB)
            pkt_type, ack_num = unpack_ack(rcv)
            print(f"SENDER (GBN): Received cumulative ACK={ack_num}. Current base={base}, nextseq={nextseqnum}.")

            if pkt_type == TYPE_ACK:
                if ack_num >= base:
                    base = ack_num + 1
                    print(f"SENDER (GBN): Window advanced. New base={base}, nextseq={nextseqnum}.\n")
                    if base == nextseqnum:
                        sent_time = None
                    else:
                        sent_time = time.time()
        except socket.timeout:
            pass

        # Timeout do pacote base
        if sent_time is not None and (time.time() - sent_time) >= TIMEOUT_S:
            print(
                f"SENDER (GBN): TIMEOUT waiting for ACK of base={base}. "
                f"Retransmitting all unacked segments in range [{base}..{nextseqnum-1}]."
            )
            for s in range(base, nextseqnum):
                pkt = buffer[s]
                time.sleep(random.uniform(DELAY_MIN_S, DELAY_MAX_S))
                sock.sendto(pkt, RECEIVER_ADDR)
                print(f"SENDER (GBN): Re-sent DATA seq={s}.")
                retransmissions += 1
            sent_time = time.time()
            print()

    print("\nSENDER (GBN): Finished sending all messages.")
    print(f"SENDER (GBN): Total retransmissions = {retransmissions}.\n")
    sock.close()


if __name__ == "__main__":
    main()


