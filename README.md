#!/usr/bin/env python3
# server.py
# UDP rendezvous + TCP relay on the same port (reads PORT env var)

import os
import socket
import threading
import time
from typing import Tuple, Dict

PORT = int(os.environ.get("PORT", "9999"))
HOST = "0.0.0.0"

# UDP rendezvous state
udp_clients: Dict[str, Tuple[str,int]] = {}
udp_lock = threading.Lock()

# TCP relay state
tcp_clients: Dict[str, socket.socket] = {}
tcp_lock = threading.Lock()

# Simple helper: print with prefix
def log(*args, **kwargs):
    print("[srv]", *args, **kwargs)

# UDP server (rendezvous)
def udp_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((HOST, PORT))
    log(f"UDP rendezvous listening on {HOST}:{PORT}")
    while True:
        try:
            data, addr = sock.recvfrom(2048)
            text = data.decode(errors="ignore").strip()
            if not text:
                continue
            parts = text.split()
            cmd = parts[0].upper()
            if cmd == "REGISTER" and len(parts) >= 2:
                cid = parts[1]
                with udp_lock:
                    udp_clients[cid] = addr
                log("REGISTER", cid, "->", addr)
                # if any other peers exist, tell both about each other (simple pairing: inform any one other)
                with udp_lock:
                    for other_id, other_addr in udp_clients.items():
                        if other_id != cid:
                            # tell this client about other
                            reply = f"PEER {other_id} {other_addr[0]} {other_addr[1]}"
                            sock.sendto(reply.encode(), addr)
                            # tell other about this client
                            reply2 = f"PEER {cid} {addr[0]} {addr[1]}"
                            sock.sendto(reply2.encode(), other_addr)
                            log("Informed", cid, "and", other_id)
                            break
            elif cmd == "PING" and len(parts) >= 2:
                cid = parts[1]
                with udp_lock:
                    udp_clients[cid] = addr
                sock.sendto(b"PONG", addr)
            elif cmd == "PUNCH":
                # forward or ack so peers know they reached the other side
                # text may be like: "PUNCH <from_id> <nonce>"
                # simply reply PUNCH-ACK
                sock.sendto(b"PUNCH-ACK", addr)
                log("PUNCH received from", addr)
            else:
                # anything else: treat as application raw bytes - in this simple server we ignore or log
                log("UDP DATA from", addr, ":", data[:80])
        except Exception as e:
            log("UDP server error:", e)
            time.sleep(0.2)

# TCP relay: accepts REGISTER <id>\n then expects framed messages:
# [4-byte big-endian length][payload bytes]
# payload expected as text "<target_id>\n<raw bytes...>"
def handle_tcp_client(conn: socket.socket, addr):
    conn.settimeout(300)
    cid = None
    try:
        # read registration line (up to newline)
        buf = b""
        while b"\n" not in buf:
            chunk = conn.recv(1024)
            if not chunk:
                log("tcp client closed before register", addr)
                conn.close()
                return
            buf += chunk
            if len(buf) > 4096:
                break
        first_line, rest = buf.split(b"\n", 1)
        parts = first_line.decode(errors="ignore").strip().split()
        if len(parts) >= 2 and parts[0].upper() == "REGISTER":
            cid = parts[1]
            with tcp_lock:
                tcp_clients[cid] = conn
            log("TCP REGISTER", cid, "from", addr)
            # if rest contains extra bytes, prepend them back to socket stream handling
            stream_buffer = rest
        else:
            log("Invalid register from", addr, "closing")
            conn.close()
            return

        # main relay loop
        while True:
            # ensure we have 4 bytes for length
            while len(stream_buffer) < 4:
                chunk = conn.recv(4096)
                if not chunk:
                    raise ConnectionError("client closed")
                stream_buffer += chunk
            length = int.from_bytes(stream_buffer[:4], "big")
            stream_buffer = stream_buffer[4:]
            while len(stream_buffer) < length:
                chunk = conn.recv(4096)
                if not chunk:
                    raise ConnectionError("client closed during payload")
                stream_buffer += chunk
            payload = stream_buffer[:length]
            stream_buffer = stream_buffer[length:]

            # payload format: first line target_id\nrest_bytes
            try:
                # try decode to split target id; if decode fails, we still try best-effort
                text = payload.decode(errors="ignore")
                if "\n" in text:
                    target_id, rest_payload = text.split("\n", 1)
                    # forward to target if connected
                    with tcp_lock:
                        target_conn = tcp_clients.get(target_id)
                    if target_conn:
                        framed = len(rest_payload.encode()).to_bytes(4, "big") + rest_payload.encode()
                        target_conn.sendall(framed)
                        log(f"Relayed {len(rest_payload)} bytes from {cid} to {target_id}")
                    else:
                        log("Target not connected:", target_id)
                else:
                    log("Malformed payload (no newline) from", cid)
            except Exception as e:
                log("Error parsing payload from", cid, e)
    except Exception as e:
        log("TCP client handler error:", e)
    finally:
        if cid:
            with tcp_lock:
                if tcp_clients.get(cid) is conn:
                    del tcp_clients[cid]
        try:
            conn.close()
        except:
            pass
        log("TCP client disconnected", addr)

def tcp_server():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen(32)
    log(f"TCP relay listening on {HOST}:{PORT}")
    while True:
        try:
            conn, addr = srv.accept()
            threading.Thread(target=handle_tcp_client, args=(conn, addr), daemon=True).start()
        except Exception as e:
            log("TCP accept error:", e)
            time.sleep(0.2)

if __name__ == "__main__":
    threading.Thread(target=udp_server, daemon=True).start()
    threading.Thread(target=tcp_server, daemon=True).start()

    # keep main thread alive
    while True:
        time.sleep(60)
