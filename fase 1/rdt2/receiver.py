import socket
import struct
import zlib

RECEIVER_ADDR = ('127.0.0.1', 12000)
SENDER_ADDR = ('127.0.0.1', 12001)

# Cabeçalho -> Primeiros bytes para identificação do tipo de pacote
TYPE_DATA = 0 # Tipo de pacote de dados -> viram bytes dps
TYPE_ACK = 1 # Tipo de pacote de ACK -> viram bytes dps
TYPE_NAK = 2 # Tipo de pacote de NAK -> viram bytes dps 

# Formato do Cabeçalho:
#  ! (network order) big-endian
#  B (1 byte tipo, sem sinal) -> Tipo de pacote
#  I (4 bytes checksum, sem sinal) -> Checksum do pacote
#  Total: 5 bytes
HEADER_FMT = '!BI'
HEADER_SIZE = struct.calcsize(HEADER_FMT)



# header = packet[:HEADER_SIZE] → primeiros 5 bytes (cabeçalho).
# data = packet[HEADER_SIZE:] → restante (payload).


# Calcula checksum -> valor inteiro 32bits calculado a aprtir do payload q veio do sender 
def verify_checksum(header, data):
    _, rcv_checksum = struct.unpack(HEADER_FMT, header) # Desempacota o cabeçalho para obter tipo do pacote (descartado) e o checksum recebido 
    calc_checksum = zlib.crc32(data) # Calcula o checksum do pacote recebido do cabeçalho (payload)

    return rcv_checksum == calc_checksum # Compara o checksum recebido com o checksum calculado, se == True, o pacote é valido, se != False, o pacote é invalido

# Cria pacote de feedback ACK/NAK -> tipo de pacote e checksum vazio
def make_feedback_pkt(pkt_type):
    data = b'' # Payload vazio, tipo de pacote nao carrega dados, len data = 0
    checksum = zlib.crc32(data) # Calcula o checksum do pacote de feedback, sempre temos checksum mesmo que seja vazio
    header = struct.pack(HEADER_FMT, pkt_type, checksum) # Cria o cabeçalho com o tipo de pacote e o checksum

    return header + data # Retorna o cabeçalho e o payload


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
            # Recebe o pacote do sender e dados do sender (ip e porta) -> (buffer de 1024 bytes) tamanho maximo do pacote 
            packet, addr = sock.recvfrom(1024)  

            # Garante que a mensagem veio do remetente esperado
            if addr != SENDER_ADDR:
                print(f"Pacote recebido de endereço inesperado {addr}. Ignorando.")
                continue

            # Desempacota o cabeçalho e separa os dados
            header = packet[:HEADER_SIZE]
            data = packet[HEADER_SIZE:]

            # Extrai o tipo de pacote e depura checksums
            pkt_type, rcv_checksum = struct.unpack(HEADER_FMT, header)
            calc_checksum = zlib.crc32(data)
            print(
                f"[RDT2][RX] from={addr} type={pkt_type} len={len(data)} "
                f"csum_rcv=0x{rcv_checksum:08X} csum_calc=0x{calc_checksum:08X}"
            )

            # Só processamos pacotes de DADOS, nao teria outro mesmo pq o receipter quem envia outros tipos...
            if pkt_type == TYPE_DATA:
                if verify_checksum(header, data):
                    # Pacote OK
                    msg = data.decode('utf-8')
                    print(f"[RDT2][RX] OK dados='{msg}'")
                    received_messages.append(msg)

                    # Envia ACK
                    print("[RDT2][RX->TX] ACK")
                    ack_pkt = make_feedback_pkt(TYPE_ACK)
                    sock.sendto(ack_pkt, SENDER_ADDR)

                else:
                    # Pacote Corrompido
                    print("[RDT2][RX] CORROMPIDO -> NAK")

                    # Envia NAK
                    print("[RDT2][RX->TX] NAK")
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