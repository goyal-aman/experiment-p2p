import os
import socket
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [CLIENT] %(levelname)s: %(message)s"
)

def send_message(host: str, port: int, message: str):
    logging.info(f"Connecting to {host}:{port}")

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        sock.connect((host, port))
        logging.info("Connected to server")

        sock.sendall(message.encode())
        logging.info(f"Sent: {message}")

        response = sock.recv(1024)
        logging.info(f"Received: {response.decode()}")

    except Exception as e:
        logging.error(f"Client error: {e}")

    finally:
        sock.close()
        logging.info("Closed connection")


if __name__ == "__main__":
    # python3 client.py tramway.proxy.rlwy.net 36332 aman
    if len(sys.argv) < 4:
        print("Usage: python client.py <host> <port> <message>")
        exit(1)

    host = sys.argv[1]
    port = int(sys.argv[2])
    message = " ".join(sys.argv[3:])

    send_message(host, port, message)
