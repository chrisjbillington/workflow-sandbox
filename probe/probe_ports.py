"""Time ways of checking whether a local TCP port has a listener."""
import socket
import statistics
import sys
import threading
import time

import zmq

sys.path.insert(0, sys.argv[1])
import ports  # labscript_utils/ports.py

N = 200


def plain_timeout(port):
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=0.1):
            return True
    except OSError:
        return False


def ioctl_blocking(port):
    with socket.socket() as sock:
        if sys.platform == 'win32':
            ports._disable_syn_retransmissions(sock)
        try:
            sock.connect(('127.0.0.1', port))
        except ConnectionRefusedError:
            return False
        return True


def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


ctx = zmq.Context()
zsock = ctx.socket(zmq.REP)
zport = zsock.bind_to_random_port('tcp://*')

listener = socket.socket()
listener.bind(('0.0.0.0', 0))
listener.listen(5)
lport = listener.getsockname()[1]


def accept_forever():
    while True:
        conn, _ = listener.accept()
        conn.close()


threading.Thread(target=accept_forever, daemon=True).start()

# A listener that does not accept, with its backlog filled.
full = socket.socket()
full.bind(('127.0.0.1', 0))
full.listen(0)
fport = full.getsockname()[1]
fillers = []
for _ in range(16):
    s = socket.socket()
    s.setblocking(False)
    try:
        s.connect(('127.0.0.1', fport))
    except (BlockingIOError, OSError):
        pass
    fillers.append(s)
time.sleep(0.5)

targets = [('free port', free_port(), False), ('zmq REP port', zport, True),
           ('plain listening socket', lport, True)]
methods = [('timeout 0.1 s (blacs 594723c)', plain_timeout),
           ('ports.port_in_use', ports.port_in_use),
           ('no retries, blocking', ioctl_blocking)]

print(f'{sys.platform} Python {sys.version.split()[0]}')
for mname, method in methods:
    for tname, port, expected in targets:
        times, wrong = [], 0
        for _ in range(N):
            t0 = time.perf_counter()
            r = method(port)
            times.append(1e3 * (time.perf_counter() - t0))
            wrong += r != expected
        times.sort()
        print(flush=True, *[f'{mname:32} {tname:24} wrong {wrong:3}/{N}  median {statistics.median(times):8.3f} ms  '
              f'p99 {times[int(0.99 * N)]:8.3f} ms  max {times[-1]:8.3f} ms'])

for mname, method in methods[:2]:
    t0 = time.perf_counter()
    r = method(fport)
    print(f'{mname:32} {"full backlog":24} result {r}  {1e3 * (time.perf_counter() - t0):8.3f} ms')
