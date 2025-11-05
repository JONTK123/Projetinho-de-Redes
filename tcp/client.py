from simple_tcp_full import SimpleTCPSocket
import time

client = SimpleTCPSocket(9000, loss_rate=0.2)

# TESTE 1: Estabelecimento
client.connect(('localhost', 8000))

# TESTE 2: Envio de dados
data = b'x' * 10240
start = time.time()
client.send(data)
elapsed = time.time() - start
print(f"[CLIENT] Enviados {len(data)} bytes em {elapsed:.3f}s")

# TESTE 6: Desempenho
throughput = (len(data) * 8) / (elapsed * 1_000_000)
print(f"[PERF] Throughput: {throughput:.3f} Mbps")
print(f"[PERF] Retransmissões: {client.retransmissions}")

# TESTE 5: Encerramento
client.close()
print("[CLIENT] Encerrado.")
