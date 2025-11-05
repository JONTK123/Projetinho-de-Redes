import socket
import struct
import threading
import random
import time

FLAG_SYN = 0b00000010
FLAG_ACK = 0b00010000
FLAG_FIN = 0b00000001

MSS = 1024  # tamanho máximo do segmento (1KB)

class SimpleTCPSocket:
    def __init__(self, port):
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.bind(('localhost', port))
        self.port = port

        self.state = 'CLOSED'
        self.seq_num = random.randint(0, 10000)
        self.ack_num = 0

        self.send_buffer = b''
        self.recv_buffer = b''

        self.recv_window = 4096
        self.peer_address = None

        self.estimated_rtt = 1.0
        self.dev_rtt = 0.5
        self.timeout = 1.0

        self.running = True
        self.lock = threading.Lock()

        # Thread de recepção
        self.recv_thread = threading.Thread(target=self._receive_loop, daemon=True)
        self.recv_thread.start()

    # =====================
    # Métodos públicos
    # =====================

    def connect(self, dest_address):
        """Three-way handshake (cliente)"""
        self.peer_address = dest_address
        self.state = 'SYN_SENT'

        # Envia SYN
        self._send_segment(FLAG_SYN)
        print("[CLIENT] -> SYN")

        # Espera SYN-ACK
        while self.state != 'ESTABLISHED':
            time.sleep(0.1)

    def listen(self):
        """Coloca socket em modo de escuta"""
        self.state = 'LISTEN'

    def accept(self):
        """Aceita conexão (three-way handshake servidor)"""
        print("[SERVER] Aguardando SYN...")
        while self.state != 'ESTABLISHED':
            time.sleep(0.1)
        print("[SERVER] Conexão estabelecida!")
        return self

    def send(self, data: bytes):
        """Envia dados em segmentos respeitando janela"""
        i = 0
        while i < len(data):
            chunk = data[i:i + MSS]
            self._send_segment(FLAG_ACK, chunk)
            i += len(chunk)
        print(f"[SEND] Enviados {len(data)} bytes")

    def recv(self, size):
        """Lê dados do buffer"""
        while len(self.recv_buffer) < size:
            time.sleep(0.05)
        data = self.recv_buffer[:size]
        self.recv_buffer = self.recv_buffer[size:]
        return data

    def close(self):
        """Encerra conexão (four-way handshake)"""
        self._send_segment(FLAG_FIN)
        print("[CLOSE] Enviado FIN")
        self.state = 'FIN_WAIT'
        while self.state != 'CLOSED':
            time.sleep(0.1)
        print("[CLOSE] Conexão encerrada.")

    # =====================
    # Funções internas
    # =====================

    def _send_segment(self, flags, data=b''):
        header = struct.pack(
            '!HHIIHHHH',
            self.port,
            0 if not self.peer_address else self.peer_address[1],
            self.seq_num,
            self.ack_num,
            (5 << 12) | flags,
            self.recv_window,
            0,
            0
        )
        segment = header + data
        if self.peer_address:
            self.udp_socket.sendto(segment, self.peer_address)
        if flags & FLAG_SYN or flags & FLAG_FIN or len(data) > 0:
            self.seq_num += max(1, len(data))

    def _parse_segment(self, segment):
        header = segment[:20]
        data = segment[20:]
        src_port, dst_port, seq, ack, offset_flags, window, checksum, urgptr = struct.unpack('!HHIIHHHH', header)
        flags = offset_flags & 0x3F
        return seq, ack, flags, window, data

    def _receive_loop(self):
        while self.running:
            try:
                segment, addr = self.udp_socket.recvfrom(4096)
                seq, ack, flags, window, data = self._parse_segment(segment)
                self._handle_segment(seq, ack, flags, window, data, addr)
            except Exception as e:
                continue

    def _handle_segment(self, seq, ack, flags, window, data, addr):
        with self.lock:
            if self.state == 'LISTEN' and flags & FLAG_SYN:
                self.peer_address = addr
                self.ack_num = seq + 1
                self._send_segment(FLAG_SYN | FLAG_ACK)
                self.state = 'SYN_RCVD'
                print("[SERVER] <- SYN | -> SYN-ACK")

            elif self.state == 'SYN_RCVD' and flags & FLAG_ACK:
                self.state = 'ESTABLISHED'
                print("[SERVER] <- ACK | Conexão ESTABELECIDA")

            elif self.state == 'SYN_SENT' and flags & FLAG_SYN and flags & FLAG_ACK:
                self.ack_num = seq + 1
                self._send_segment(FLAG_ACK)
                self.state = 'ESTABLISHED'
                print("[CLIENT] <- SYN-ACK | -> ACK | Conexão ESTABELECIDA")

            elif self.state == 'ESTABLISHED':
                if len(data) > 0:
                    self.recv_buffer += data
                    self.ack_num = seq + len(data)
                    self._send_segment(FLAG_ACK)
                if flags & FLAG_FIN:
                    self.ack_num = seq + 1
                    self._send_segment(FLAG_ACK)
                    self.state = 'CLOSED'
                    print("[RECV] <- FIN | -> ACK | CLOSED")

            elif self.state == 'FIN_WAIT' and flags & FLAG_ACK:
                self.state = 'CLOSED'

    def _calculate_timeout(self):
        return self.estimated_rtt + 4 * self.dev_rtt

    def _update_rtt(self, sample_rtt):
        self.estimated_rtt = 0.875 * self.estimated_rtt + 0.125 * sample_rtt
        self.dev_rtt = 0.75 * self.dev_rtt + 0.25 * abs(sample_rtt - self.estimated_rtt)
        self.timeout = self._calculate_timeout()
