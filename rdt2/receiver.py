# receiver.py

import socket
import struct
import zlib

RECEIVER_ADDR = ('127.0.0.1', 12000)
SENDER_ADDR = ('127.0.0.1', 12001)

TYPE_DATA = 0
TYPE_ACK = 1
TYPE_NAK = 2

# Formato do Cabeçalho: ! (network order), B (1 byte tipo), I (4 bytes checksum)
HEADER_FMT = '!BI'
HEADER_SIZE = struct.calcsize(HEADER_FMT)


def verify_checksum(header, data):
    _, rcv_checksum = struct.unpack(HEADER_FMT, header)
    calc_checksum = zlib.crc32(data)

    return rcv_checksum == calc_checksum


def make_feedback_pkt(pkt_type):
    data = b''
    checksum = zlib.crc32(data)
    header = struct.pack(HEADER_FMT, pkt_type, checksum)
    return header + data


def main():
    # Cria o socket UDP
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Associa o socket ao endereço do receptor
    sock.bind(RECEIVER_ADDR)

    print(f"Receptor ouvindo em {RECEIVER_ADDR}")

    received_messages = []

    # Loop para receber as 10 mensagens
    while len(received_messages) < 10:
        try:
            # Recebe o pacote (buffer de 1024 bytes)
            packet, addr = sock.recvfrom(1024)

            # Garante que a mensagem veio do remetente esperado
            if addr != SENDER_ADDR:
                print(f"Pacote recebido de endereço inesperado {addr}. Ignorando.")
                continue

            # Desempacota o cabeçalho e separa os dados
            header = packet[:HEADER_SIZE]
            data = packet[HEADER_SIZE:]

            # Extrai o tipo de pacote
            pkt_type, _ = struct.unpack(HEADER_FMT, header)

            # Só processamos pacotes de DADOS
            if pkt_type == TYPE_DATA:
                if verify_checksum(header, data):
                    # Pacote OK
                    msg = data.decode('utf-8')
                    print(f"Pacote recebido: OK. Dados: '{msg}'")
                    received_messages.append(msg)

                    # Envia ACK
                    print("Enviando ACK...")
                    ack_pkt = make_feedback_pkt(TYPE_ACK)
                    sock.sendto(ack_pkt, SENDER_ADDR)

                else:
                    # Pacote Corrompido
                    print("Pacote recebido: CORRUPTO.")

                    # Envia NAK
                    print("Enviando NAK...")
                    nak_pkt = make_feedback_pkt(TYPE_NAK)
                    sock.sendto(nak_pkt, SENDER_ADDR)

        except Exception as e:
            print(f"Erro ao receber pacote: {e}")

    print("\n--- Transmissão Concluída ---")
    print("Total de 10 mensagens recebidas corretamente.")
    print("Mensagens:")
    for i, msg in enumerate(received_messages):
        print(f"  {i + 1}: {msg}")

    sock.close()


if __name__ == "__main__":
    main()