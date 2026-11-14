#!/usr/bin/env python3
"""Detect serial-lock stalls from daemon logs without competing for Optolink."""
import json
import os
from pathlib import Path
import subprocess
import time

SERVICE = 'vcontrol.service'
BOOT = Path('/proc/sys/kernel/random/boot_id')
LOG = Path('/var/log/vcontrold.log')
STATE = Path('/var/lib/viessmann-watchdog/state.json')
STALL = 120
COOLDOWN = 600


def observe(state, text, now):
    """Require recent lock requests with no acquisition or serial progress."""
    for line in text.splitlines():
        if 'tries to aquire lock' in line:
            state.setdefault('blocked_since', now)
            state['last_request'] = now
        elif ('got lock' in line or '>SENT:' in line or '<RECV:' in line):
            state.pop('blocked_since', None)
            state.pop('last_request', None)
    return (now - state.get('blocked_since', now) >= STALL
            and now - state.get('last_request', 0) <= 90
            and now - state.get('last_restart', -COOLDOWN) >= COOLDOWN)


def check():
    # Deliberate stops must remain stopped. systemd supervises unexpected exits.
    if subprocess.run(['systemctl', 'is-active', '--quiet', SERVICE]).returncode:
        return
    now = time.monotonic()
    boot = BOOT.read_text().strip()
    try:
        state = json.loads(STATE.read_text())
    except (FileNotFoundError, ValueError):
        state = {}
    if state.get('boot') != boot:
        state = {'boot': boot}
    with LOG.open('rb') as stream:
        stat = os.fstat(stream.fileno())
        identity = [stat.st_dev, stat.st_ino]
        offset = state.get('offset', stat.st_size)
        if state.get('log') != identity or offset > stat.st_size:
            # New/rotated log: establish a baseline, never act on historical lines.
            state.pop('blocked_since', None)
            state.pop('last_request', None)
            offset = stat.st_size
        if stat.st_size - offset > 1024 * 1024:
            # Lost evidence cannot establish an uninterrupted stall.
            state.pop('blocked_since', None)
            state.pop('last_request', None)
            offset = stat.st_size
        stream.seek(offset)
        data = stream.read()
        # Keep an incomplete final line for the next check.
        end = data.rfind(b'\n') + 1
        state.update(log=identity, offset=offset + end)
    restart = observe(state, data[:end].decode('utf-8', errors='replace'), now)
    if restart:
        state['last_restart'] = now
        state.pop('blocked_since', None)
        state.pop('last_request', None)
    STATE.parent.mkdir(parents=True, exist_ok=True)
    temporary = STATE.with_suffix('.tmp')
    temporary.write_text(json.dumps(state))
    temporary.replace(STATE)
    if restart:
        print('Serial lock requests without progress for 120s; restarting vcontrold', flush=True)
        subprocess.run(['systemctl', 'restart', SERVICE], check=True, timeout=45)


if __name__ == '__main__':
    check()
