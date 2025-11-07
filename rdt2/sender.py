import socket
import struct
import zlib
import random


RECEIVER_ADDR = ('127.0.0.1', 12000)
SENDER_ADDR = ('127.0.0.1', 12001)

TYPE_DATA = 0
TYPE_ACK = 1
TYPE_NAK = 2

# Formato do Cabeçalho: ! (network order), B (1 byte tipo), I (4 bytes checksum)
HEADER_FMT = '!BI'
HEADER_SIZE = struct.calcsize(HEADER_FMT)

# Para o Teste 1: use 0.0
# Para o Teste 2: use 0.3
PROB_CORRUPCAO = 0.3


def make_data_pkt(data):
    checksum = zlib.crc32(data)
    header = struct.pack(HEADER_FMT, TYPE_DATA, checksum)
    return header + data


def corrupt_packet(packet, prob):
    if random.random() < prob:
        print("[Simulação] Corrompendo pacote...")

        # Escolhe um índice aleatório no pacote para inverter um bit
        idx = random.randint(0, len(packet) - 1)
        # Pega o byte original
        original_byte = packet[idx]
        # Escolhe um bit aleatório (0-7) para inverter
        bit_to_flip = 1 << random.randint(0, 7)
        # Inverte o bit usando XOR
        corrupted_byte = original_byte ^ bit_to_flip

        # Reconstrói o pacote com o byte corrompido
        pkt_list = list(packet)
        pkt_list[idx] = corrupted_byte
        return bytes(pkt_list)

    return packet


def unpack_feedback_pkt(packet):
    """Desempacota um pacote de ACK/NAK."""
    header = packet[:HEADER_SIZE]
    pkt_type, _ = struct.unpack(HEADER_FMT, header)
    return pkt_type


def main():
    # Cria o socket UDP
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Associa o socket ao endereço do remetente
    sock.bind(SENDER_ADDR)

    # RDT 2.0 não tem timeout, mas é uma boa prática ter um
    # O remetente ficará bloqueado em recvfrom()

    messages = [f"Mensagem {i}" for i in range(1, 11)]
    retransmissions = 0

    print(f"Remetente pronto para enviar {len(messages)} mensagens para {RECEIVER_ADDR}")
    print(f"Probabilidade de corrupção: {PROB_CORRUPCAO * 100}%\n")

    for msg in messages:
        print(f"--- Enviando: '{msg}' ---")

        # Cria o pacote de dados
        sndpkt = make_data_pkt(msg.encode('utf-8'))

        # Loop "Stop-and-Wait" (FSM do RDT 2.0)
        while True:
            # Corrompe o pacote artificialmente (ou não)
            pkt_to_send = corrupt_packet(sndpkt, PROB_CORRUPCAO)

            # Envia o pacote
            sock.sendto(pkt_to_send, RECEIVER_ADDR)
            print("Pacote enviado. Aguardando ACK/NAK...")

            try:
                # Espera bloqueado pela resposta
                rcvpkt, addr = sock.recvfrom(1024)

                # Desempacota o feedback
                pkt_type = unpack_feedback_pkt(rcvpkt)

                if pkt_type == TYPE_NAK:
                    print("NAK recebido. Retransmitindo...")
                    retransmissions += 1
                    # O loop continua (retransmite)

                elif pkt_type == TYPE_ACK:
                    print("ACK recebido. Próxima mensagem.\n")
                    # Sai do loop e vai para a próxima mensagem
                    break

            except socket.timeout:
                # Embora RDT 2.0 não preveja perda, se tivéssemos um timeout:
                print("Timeout! (Não deveria acontecer no RDT 2.0). Retransmitindo...")
                retransmissions += 1

    print("--- Transmissão Concluída ---")
    print(f"Total de retransmissões: {retransmissions}")
    sock.close()


if __name__ == "__main__":
    main()