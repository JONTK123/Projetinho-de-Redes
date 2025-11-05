from simple_tcp import SimpleTCPSocket

server = SimpleTCPSocket(8000)
server.listen()
conn = server.accept()

print("[SERVER] Aguardando dados...")
data = conn.recv(10240)
print(f"[SERVER] Recebidos {len(data)} bytes")

conn.close()
print("[SERVER] Encerrado.")
