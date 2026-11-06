"""Single-owner, read-only vcontrold polling; independent of Indigo."""
from dataclasses import dataclass, field
import math
import re
import socket
import time

# Existing script mappings, checked against the deployed XML; live validation pending.
READS = {'boilerTemp': 'getBoilerTemp', 'outsideTemp': 'getOutsideTemp',
         'roomSetpoint': 'getRoomTempSP', 'warmWaterTemp': 'getWaterTemp'}
TARGETS = {'standard': ('getRoomTempSP', 'setTempRaumNorSollM1'),
           'reduced': ('getTempRaumRedSollM1', 'setTempRaumRedSollM1'),
           'party': ('getTempPartyM1', 'setTempPartyM1'),
           'dhw': ('getTempWWsoll', 'setTempWWsoll')}
SIMULATOR_ID = 'SIMULATOR_209F (ID=209F) (Protocol=KW2)'
TEMPERATURE = re.compile(r'([+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+))(?:[ \t]*(?:°?C))?')


def temperature(text):
    match = TEMPERATURE.fullmatch(text.strip())
    if not match:
        raise ValueError('Invalid reading: ' + text.strip()[:160])
    value = float(match.group(1))
    if not math.isfinite(value):
        raise ValueError('Non-finite reading')
    return value


@dataclass(frozen=True)
class Settings:
    host: str
    port: int = 3002
    interval: int = 180
    timeout: int = 12
    enabled: bool = False
    target: str = "standard"

    def __post_init__(self):
        if self.target not in ('standard', 'reduced', 'party'):
            raise ValueError('Invalid room target')
        if not self.host or any(c.isspace() for c in self.host):
            raise ValueError('A hostname or IP address is required')
        for value, low, high in ((self.port, 1, 65535), (self.interval, 30, 86400),
                                 (self.timeout, 1, 60)):
            if not isinstance(value, int) or not low <= value <= high:
                raise ValueError('Connection settings outside allowed range')


@dataclass
class Result:
    values: dict = field(default_factory=dict)
    errors: dict = field(default_factory=dict)
    tcp_available: bool = False
    release_error: str = ''
    simulator: bool = False


class Client:
    """Persistent TCP; release Optolink after each cycle. Not thread-safe by design."""
    def __init__(self, settings):
        self.settings = settings
        self.sock = None
        self.buffer = b''

    def disconnect(self):
        if self.sock is not None:
            self.sock.close()
        self.sock = None
        self.buffer = b''

    def _frame(self, cancelled):
        deadline = time.monotonic() + self.settings.timeout
        while b'vctrld>' not in self.buffer:
            if cancelled():
                raise InterruptedError('Polling cancelled')
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('vcontrold response deadline exceeded')
            self.sock.settimeout(min(0.25, remaining))
            try:
                chunk = self.sock.recv(4096)
            except socket.timeout:
                continue
            if not chunk:
                raise ConnectionError('vcontrold disconnected')
            self.buffer += chunk
            if len(self.buffer) > 65536:
                raise ValueError('Response exceeds 64 KiB')
        frame, self.buffer = self.buffer.split(b'vctrld>', 1)
        # Current protocol has no unsolicited messages. Do not parse arbitrary digits.
        return frame.decode('ascii').strip()

    def _exchange(self, command, cancelled):
        allowed = set(READS.values()) | {v[0] for v in TARGETS.values()} | {'getProbeRoomTemp', 'device', 'close'}
        if command not in allowed:
            raise ValueError('Command is not an allowed read or link release')
        self.sock.settimeout(self.settings.timeout)
        self.sock.sendall((command + '\n').encode('ascii'))
        return self._frame(cancelled)

    def poll(self, cancelled=lambda: False):
        result = Result()
        try:
            if self.sock is None:
                self.sock = socket.create_connection(
                    (self.settings.host, self.settings.port), min(5, self.settings.timeout))
                result.tcp_available = True
                self._frame(cancelled)
            result.tcp_available = True
            try:
                try:
                    result.simulator = self._exchange('device', cancelled) == SIMULATOR_ID
                except (OSError, ValueError, UnicodeError):
                    self.disconnect()
                    raise
                reads = dict(READS)
                reads['roomSetpoint'] = TARGETS[self.settings.target][0]
                if result.simulator:
                    reads.update(roomMeasuredTemp='getProbeRoomTemp', dhwSetpoint='getTempWWsoll')
                for key, command in reads.items():
                    try:
                        response = self._exchange(command, cancelled)
                    except (OSError, ValueError, UnicodeError):
                        # Framing/transport failure: never send more commands on this stream.
                        self.disconnect()
                        raise
                    try:
                        result.values[key] = temperature(response)
                    except ValueError as exc:
                        result.errors[key] = str(exc)
            finally:
                if self.sock is not None:
                    try:
                        response = self._exchange('close', cancelled)
                        if not response.endswith(' closed') or 'ERR:' in response:
                            raise ValueError('Unexpected Optolink release response')
                    except (OSError, ValueError, UnicodeError) as exc:
                        result.release_error = str(exc)
                        self.disconnect()
        except (OSError, ValueError, UnicodeError) as exc:
            self.disconnect()
            for key in READS:
                if key not in result.values and key not in result.errors:
                    result.errors[key] = (str(exc) if result.tcp_available else
                                          f"Connect to {self.settings.host}:{self.settings.port} failed: {exc}")
        return result


    def write_simulated(self, target, value, cancelled=lambda: False):
        """No physical writes: fresh identity check, bounded setter, then real readback."""
        if target not in TARGETS:
            raise ValueError('Unknown target')
        number = float(value)
        low, high = (10, 60) if target == 'dhw' else (3, 37)
        if not math.isfinite(number) or not number.is_integer() or not low <= number <= high:
            raise ValueError('Simulator target must be a whole degree from %s to %s' % (low, high))
        try:
            if self.sock is None:
                self.sock = socket.create_connection((self.settings.host, self.settings.port), min(5, self.settings.timeout))
                self._frame(cancelled)
            # Check on this exact connection immediately before the one permitted write.
            if self._exchange('device', cancelled) != SIMULATOR_ID:
                raise PermissionError('Setpoint writes are enabled only on the marked simulator')
            if cancelled():
                raise InterruptedError('Cancelled before write')
            read, setter = TARGETS[target]
            self.sock.settimeout(self.settings.timeout)
            self.sock.sendall(('%s %d\n' % (setter, number)).encode('ascii'))
            if self._frame(cancelled) != 'OK':
                raise ValueError('Setter did not return OK; result uncertain, not retried')
            actual = temperature(self._exchange(read, cancelled))
            if actual != number:
                raise ValueError('Setpoint readback mismatch')
            response = self._exchange('close', cancelled)
            if not response.endswith(' closed') or 'ERR:' in response:
                raise ValueError('Optolink release failed after write')
            return actual
        except (OSError, ValueError, UnicodeError):
            self.disconnect()
            raise


class Manager:
    """One physical system and one serialized command stream for all child devices."""
    def __init__(self, clock=time.monotonic, client_factory=Client):
        self.clock = clock
        self.client_factory = client_factory
        self.settings = None
        self.client = None
        self.due = 0
        self.requested = False

    def configure(self, settings):
        if settings != self.settings:
            self.close()
            self.settings = settings
            self.due = self.clock()

    def request_poll(self):
        # Called only by the worker; repeated queued refresh requests coalesce.
        self.requested = True

    def tick(self, cancelled=lambda: False):
        if (self.settings is None or cancelled()
                or (not self.requested and (not self.settings.enabled or self.clock() < self.due))):
            return None
        if self.client is None:
            self.client = self.client_factory(self.settings)
        self.requested = False
        result = self.client.poll(cancelled)
        # No overlapping cycles or catch-up burst if a cycle takes longer than expected.
        self.due = self.clock() + self.settings.interval
        return result

    def write_simulated(self, target, value, cancelled=lambda: False):
        if self.settings is None or not self.settings.enabled:
            raise PermissionError('Polling must be enabled to use simulator controls')
        if self.client is None:
            self.client = self.client_factory(self.settings)
        actual = self.client.write_simulated(target, value, cancelled)
        self.due = self.clock()
        return actual

    def close(self):
        self.requested = False
        if self.client is not None:
            self.client.disconnect()
        self.client = None
