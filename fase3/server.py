from simple_tcp_full import SimpleTCPSocket
import time

server = SimpleTCPSocket(8000, loss_rate=0.2)
server.listen()
conn = server.accept()

# TESTE 2: Transferência de dados
print("\n[TESTE 2] Recebendo 10 KB...")
data = conn.recv(10240)
print(f"[SERVER] Recebidos {len(data)} bytes")

# TESTE 5: Encerramento
print("\n[TESTE 5] Encerrando conexão...")
time.sleep(1)
conn.close()
print("[SERVER] Encerrado.\n")
