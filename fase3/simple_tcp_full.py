import socket
import struct
import threading
import random
import time

# -----------------------------
#  Definições de Flags e Const
# -----------------------------
FLAG_FIN = 0b00000001
FLAG_SYN = 0b00000010
FLAG_ACK = 0b00010000
MSS = 1024  # Segmento de 1 KB


class SimpleTCPSocket:
    def __init__(self, port, loss_rate=0.2):
        # UDP subjacente
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.bind(('localhost', port))
        self.port = port

        # Estados
        self.state = 'CLOSED'
        self.peer_address = None

        # Controle de sequência e ACK
        self.seq_num = random.randint(0, 10000)
        self.ack_num = 0

        # Buffers
        self.send_buffer = b''
        self.recv_buffer = b''

        # Controle de fluxo
        self.recv_window = 4096
        self.peer_window = 4096

        # RTT / Timeout
        self.estimated_rtt = 0.5
        self.dev_rtt = 0.25
        self.timeout = self._calculate_timeout()

        # Retransmissões
        self.unacked_segments = {}
        self.retransmissions = 0
        self.loss_rate = loss_rate

        # Controle de execução
        self.running = True
        self.lock = threading.Lock()

        # Threads
        self.recv_thread = threading.Thread(target=self._receive_loop, daemon=True)
        self.timer_thread = threading.Thread(target=self._timeout_loop, daemon=True)
        self.recv_thread.start()
        self.timer_thread.start()

    # ==========================================================
    # Métodos principais públicos (API)
    # ==========================================================

    def connect(self, dest_address):
        """Cliente: inicia handshake"""
        self.peer_address = dest_address
        self.state = 'SYN_SENT'
        self._send_segment(FLAG_SYN)
        print("[CLIENT] -> SYN")

        while self.state != 'ESTABLISHED':
            time.sleep(0.05)
        print("[CLIENT] <- SYN-ACK -> ACK | Conexão ESTABELECIDA")

    def listen(self):
        """Servidor: modo escuta"""
        self.state = 'LISTEN'

    def accept(self):
        """Servidor: espera handshake"""
        print("[SERVER] Aguardando SYN...")
        while self.state != 'ESTABLISHED':
            time.sleep(0.05)
        print("[SERVER] Conexão estabelecida!")
        return self

    def send(self, data):
        """Envia dados respeitando janela"""
        i = 0
        while i < len(data):
            with self.lock:
                janela = min(self.peer_window, MSS)
            if janela <= 0:
                time.sleep(0.05)
                continue

            chunk = data[i:i + janela]
            self._send_segment(FLAG_ACK, chunk)
            i += janela
        print(f"[SEND] Enviados {len(data)} bytes")

    def recv(self, size):
        """Recebe dados (bloqueante)"""
        while len(self.recv_buffer) < size:
            time.sleep(0.05)
        with self.lock:
            data = self.recv_buffer[:size]
            self.recv_buffer = self.recv_buffer[size:]
        return data

    def close(self):
        """Encerra conexão (four-way handshake)"""
        self._send_segment(FLAG_FIN)
        self.state = 'FIN_WAIT'
        print("[CLOSE] -> FIN")

        # Aguarda confirmação
        start = time.time()
        while self.state != 'CLOSED' and time.time() - start < 5:
            time.sleep(0.1)
        print("[CLOSE] Conexão encerrada")
        self.running = False
        self.udp_socket.close()

    # ==========================================================
    # Funções internas de envio/recepção
    # ==========================================================

    def _send_segment(self, flags, data=b''):
        """Monta e envia segmento TCP simplificado"""
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

        # Simulação de perda
        if random.random() < self.loss_rate and (len(data) > 0 or flags & FLAG_ACK):
            print("[LOSS] Pacote perdido (simulado)")
            return

        # Envia
        if self.peer_address:
            self.udp_socket.sendto(segment, self.peer_address)

        # Armazena se for necessário confirmar
        if flags & (FLAG_SYN | FLAG_FIN) or len(data) > 0:
            self.unacked_segments[self.seq_num] = (segment, time.time())
            self.seq_num += max(1, len(data))

        print(f"[SEND] flags={flags:06b} seq={self.seq_num} ack={self.ack_num} len={len(data)}")

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
            except Exception:
                continue

    def _timeout_loop(self):
        """Verifica timeouts e retransmite"""
        while self.running:
            now = time.time()
            resend = []
            with self.lock:
                for seq, (seg, t0) in list(self.unacked_segments.items()):
                    if now - t0 > self.timeout:
                        resend.append(seq)
            for seq in resend:
                with self.lock:
                    seg, _ = self.unacked_segments[seq]
                    self.udp_socket.sendto(seg, self.peer_address)
                    self.unacked_segments[seq] = (seg, time.time())
                    self.retransmissions += 1
                    print(f"[RETRANS] Retransmitindo seq={seq}")
            time.sleep(0.05)

    # ==========================================================
    # Processamento dos segmentos recebidos
    # ==========================================================

    def _handle_segment(self, seq, ack, flags, window, data, addr):
        with self.lock:
            print(f"[RECV] flags={flags:06b} seq={seq} ack={ack} len={len(data)} state={self.state}")
            self.peer_window = window
            self.peer_address = addr

            if self.state == 'LISTEN' and flags & FLAG_SYN:
                self.ack_num = seq + 1
                self._send_segment(FLAG_SYN | FLAG_ACK)
                self.state = 'SYN_RCVD'

            elif self.state == 'SYN_RCVD' and flags & FLAG_ACK:
                self.state = 'ESTABLISHED'

            elif self.state == 'SYN_SENT' and flags & FLAG_SYN and flags & FLAG_ACK:
                self.ack_num = seq + 1
                self._send_segment(FLAG_ACK)
                self.state = 'ESTABLISHED'

            elif self.state == 'ESTABLISHED':
                if len(data) > 0:
                    self.recv_buffer += data
                    self.ack_num = seq + len(data)
                    self._send_segment(FLAG_ACK)
                if flags & FLAG_ACK:
                    self._acknowledge(ack)
                if flags & FLAG_FIN:
                    self.ack_num = seq + 1
                    self._send_segment(FLAG_ACK)
                    self.state = 'CLOSED'

            elif self.state == 'FIN_WAIT' and flags & FLAG_ACK:
                self._acknowledge(ack)
                self.state = 'CLOSED'

    def _acknowledge(self, ack):
        """Remove segmentos confirmados"""
        self.unacked_segments = {
            s: (seg, t)
            for s, (seg, t) in self.unacked_segments.items()
            if s >= ack
        }

    # ==========================================================
    # RTT e Timeout adaptativo
    # ==========================================================
    def _calculate_timeout(self):
        return self.estimated_rtt + 4 * self.dev_rtt

    def _update_rtt(self, sample_rtt):
        self.estimated_rtt = 0.875 * self.estimated_rtt + 0.125 * sample_rtt
        self.dev_rtt = 0.75 * self.dev_rtt + 0.25 * abs(sample_rtt - self.estimated_rtt)
        self.timeout = self._calculate_timeout()
