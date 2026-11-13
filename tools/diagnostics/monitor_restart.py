#!/usr/bin/env python3
"""Read-only restart/fault-clear capture; JSONL output, no setters or resets."""
import argparse
import datetime as dt
import json
import signal
import socket
import threading
import time

COMMANDS = ('device', 'getSystemTime', 'getError0', 'getProbeRelayStatus')
stop = threading.Event()
for sig in (signal.SIGTERM, signal.SIGINT):
    signal.signal(sig, lambda *_: stop.set())

def frame(sock):
    data = b''
    while b'vctrld>' not in data:
        block = sock.recv(4096)
        if not block:
            raise ConnectionError('daemon disconnected')
        data += block
        if len(data) > 65536:
            raise ValueError('response too large')
    return data.split(b'vctrld>', 1)[0].decode('ascii', errors='replace').strip()

def sample(host, port, timeout):
    row = {'started_utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'responses': {}, 'observed_utc': {}}
    start = time.monotonic()
    sock = None
    try:
        sock = socket.create_connection((host, port), timeout)
        sock.settimeout(timeout)
        frame(sock)
        for command in COMMANDS:
            if stop.is_set():
                break
            sock.sendall((command + '\n').encode('ascii'))
            row['responses'][command] = frame(sock)
            row['observed_utc'][command] = dt.datetime.now(dt.timezone.utc).isoformat()
        sock.sendall(b'close\n')
        row['release'] = frame(sock)
    except (OSError, ValueError) as exc:
        row['error'] = str(exc)
    finally:
        if sock is not None:
            sock.close()  # releases ownership even when framing failed
    row['finished_utc'] = dt.datetime.now(dt.timezone.utc).isoformat()
    row['duration_seconds'] = round(time.monotonic() - start, 3)
    return row

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--host', default='127.0.0.1')
    p.add_argument('--port', type=int, default=3002)
    p.add_argument('--interval', type=float, default=30)
    p.add_argument('--timeout', type=float, default=12)
    p.add_argument('--once', action='store_true')
    args = p.parse_args()
    if args.interval <= 0 or args.timeout <= 0:
        p.error('interval and timeout must be positive')
    previous = None
    while not stop.is_set():
        start = time.monotonic()
        row = sample(args.host, args.port, args.timeout)
        tracked = {k: v for k, v in row['responses'].items() if k != 'getSystemTime'}
        row['changed'] = previous is not None and tracked != previous
        previous = tracked
        print(json.dumps(row), flush=True)
        if args.once:
            break
        # Start-to-start cadence; no overlap or catch-up bursts on a slow cycle.
        stop.wait(max(0, args.interval - (time.monotonic() - start)))

if __name__ == '__main__':
    main()
