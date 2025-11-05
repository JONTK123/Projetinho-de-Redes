from simple_tcp import SimpleTCPSocket
import time

client = SimpleTCPSocket(9000)
client.connect(('localhost', 8000))

data = b'x' * 10240
start = time.time()
client.send(data)
elapsed = time.time() - start
print(f"[CLIENT] Enviados {len(data)} bytes em {elapsed:.3f}s")

client.close()
print("[CLIENT] Encerrado.")
