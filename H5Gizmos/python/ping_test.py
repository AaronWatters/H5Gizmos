"""
Host pingability test adappted from
https://stackoverflow.com/questions/2953462/pinging-servers-in-python
"""

import platform    # For getting the operating system name
import subprocess  # For executing a shell command
from multiprocessing import Process
import socket
import time

def pingable(host):
    """
    Returns True if host (str) responds to a ping request.
    Remember that a host may not respond to a ping (ICMP) request even if the host name is valid.
    """

    # Option for the number of packets as a function of
    param = '-n' if platform.system().lower()=='windows' else '-c'

    # Building the command. Ex: "ping -c 1 google.com"
    command = ['ping', param, '1', host]

    return subprocess.call(command) == 0

SERVER_TIMEOUT = 0.5
CLIENT_DELAY = 0.1
MESSAGE = b"testing testing 1 2 3"
VERBOSE = False

class LoopServer:

    def __init__(self, host, port, backlog=5):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(SERVER_TIMEOUT)
        sock.bind((host, port))
        sock.listen(backlog)
        self.sock = sock
        if VERBOSE:
            print("SERVER LISTENING")

    def accept(self):
        sock = self.sock
        if VERBOSE:
            print("SERVER accepting", (host, port))
        try:
            (conn, addr) = sock.accept()
            try:
                data = conn.recv(1024)
                if VERBOSE:
                    print("SERVER got", repr(data))
            finally:
                conn.close()
        finally:
            sock.close()
        return data

def loop_client(host, port, message=MESSAGE):
    time.sleep(CLIENT_DELAY)
    if VERBOSE:
        print("CLIENT sending", (host, port, message))
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((host, port))
        sock.send(message)
    finally:
        sock.close()

def loop_test(host, port):
    try:
        server = LoopServer(host, port)
        client_process = Process(target=loop_client, args=(host, port))
        client_process.start()
        data = server.accept()
        client_process.join()
        assert data == MESSAGE
        if VERBOSE:
            print ("loop succeeded", host, port)
        return True
    except Exception as e:
        if VERBOSE:
            print("loop exception", e)
        return False

if __name__ == "__main__":
    VERBOSE = True
    host = "localhost"
    port = 9991
    if 1:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        print("hostname", hostname, "local ip", local_ip)
        host = local_ip
    test = loop_test(host, port)
