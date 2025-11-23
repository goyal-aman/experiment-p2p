import os
import socket
import logging

# ---- Logging ----
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [SERVER] %(levelname)s: %(message)s"
)

def start_server():
    PORT = int(os.getenv("PORT", "8000"))

    logging.info(f"Reading PORT from env: {PORT}")

    # Create TCP socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    logging.info("Created TCP socket")

    # Reuse address
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    logging.info("Enabled SO_REUSEADDR")

    # Bind
    server_socket.bind(("0.0.0.0", PORT))
    logging.info(f"Bound to 0.0.0.0:{PORT}")

    # Listen
    server_socket.listen(5)
    logging.info("Listening for incoming connections...")

    while True:
        logging.info("Waiting for new client...")
        conn, addr = server_socket.accept()
        logging.info(f"Client connected: {addr}")

        try:
            while True:
                data = conn.recv(1024)
                if not data:
                    logging.info(f"Client {addr} disconnected")
                    break

                logging.info(f"Received: {data}")
                conn.sendall(data)
                logging.info(f"Sent back: {data}")

        except Exception as e:
            logging.error(f"Error with client {addr}: {e}")

        finally:
            conn.close()
            logging.info(f"Closed connection with {addr}")


if __name__ == "__main__":
    start_server()
