# rendezvous_tcp.py
import socket
import threading, os
import logging 

# ---- Logging ----
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [SERVER] %(levelname)s: %(message)s"
)


HOST = '0.0.0.0'
PORT = int(os.environ.get('PORT', 9678))    # change to your public port

clients = {}   # id -> (ip, port, conn)

lock = threading.Lock()

def handle(conn, addr):
    try:
        f = conn.makefile('rwb', buffering=0)
        line = f.readline().decode().strip()
        # expect: REGISTER <id> <port>
        parts = line.split()
        logging.info("addr ", addr)
        if len(parts) >= 3 and parts[0].upper() == 'REGISTER':
            cid = parts[1]
            try:
                peer_listen_port = int(parts[2])
            except:
                conn.sendall(b'ERR bad port\n')
                conn.close()
                return
            with lock:
                clients[cid] = (addr[0], peer_listen_port, conn)
                print(f"Registered {cid} from {addr[0]}:{peer_listen_port}")
                # look for another client with same pair? We will pair when two different ids are present:
                # For demo: we assume peer id is the other id (caller supplies it) - simpler: client will ask for a peer id.
                # But here we respond with a list of all clients excluding itself.
                peers = [(k, v[0], v[1]) for k, v in clients.items() if k != cid]
            # send peers (simple format)
            for p in peers:
                line = f"PEER {p[0]} {p[1]} {p[2]}\n"
                conn.sendall(line.encode())
        else:
            conn.sendall(b'ERR expected REGISTER <id> <port>\n')
    except Exception as e:
        print("handle err", e)
    finally:
        try:
            conn.close()
        except:
            pass

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((HOST, PORT))
    sock.listen(50)
    print("Rendezvous server listening on", HOST, PORT)
    
    while True:
        logging.info("AWAITING CONNECTION")
        conn, addr = sock.accept()
        # logging.info("CONNECTION ACCEPTED", conn, addr)
        threading.Thread(target=handle, args=(conn, addr), daemon=True).start()

if __name__ == '__main__':
    main()
