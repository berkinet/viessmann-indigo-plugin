"""Single-owner vcontrold polling and explicitly authorized setpoints; independent of Indigo."""
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
LIVE_ID = 'V200KO2B (ID=209F) (Protocol=KW2)'
LIVE_TARGETS = {'standard', 'dhw'}
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
    activity_probe: bool = True
    live_writes: bool = False

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
    live_identity: bool = False
    optical_activity: str = 'Unavailable'
    optical_error: str = ''
    optical_checked: bool = False
    # Reserved for a verified CURRENT fault producer, never history alone.
    verified_active_fault_code: str = ''


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

    def _activity_probe(self, result, identity, cancelled):
        if not self.settings.activity_probe:
            result.optical_activity = 'Disabled'
            return
        # P300 framing can transmit on open/close. Restrict passive raw access
        # to our known unframed KW protocols, never arbitrary user raw commands.
        if not identity.endswith(('(Protocol=KW)', '(Protocol=KW2)')):
            result.optical_activity = 'Unsupported'
            return
        if cancelled():
            raise InterruptedError('Polling cancelled')
        result.optical_checked = True
        try:
            self.sock.settimeout(self.settings.timeout)
            self.sock.sendall(b'raw\nRECV 1\nEND\n')
            reply = self._frame(cancelled)
            if re.fullmatch(r'Result: +05', reply):
                result.optical_activity = 'Detected'
            elif re.fullmatch(r'Result: +[0-9A-Fa-f]{2}', reply):
                result.optical_activity = 'Unexpected byte'
                result.optical_error = reply
            else:
                result.optical_activity = 'Not detected'
                result.optical_error = reply[:400] or 'No byte returned by receive-only probe'
        except (OSError, ValueError, UnicodeError) as exc:
            # Raw RECV exits the vcontrold child on receive timeout. A missing
            # Result is not proof of power-off; keep the actual diagnostic.
            result.optical_activity = 'Not detected'
            result.optical_error = str(exc)
            self.disconnect()
            if cancelled():
                raise InterruptedError('Polling cancelled')
            # Never reuse an ambiguous raw-mode stream. Normal polling gets
            # a fresh TCP session, still owned by this same serial manager.
            self.sock = socket.create_connection(
                (self.settings.host, self.settings.port), min(5, self.settings.timeout))
            self._frame(cancelled)

    def poll(self, cancelled=lambda: False, on_progress=None):
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
                    identity = self._exchange('device', cancelled)
                    result.simulator = identity == SIMULATOR_ID
                    result.live_identity = identity == LIVE_ID
                    self._activity_probe(result, identity, cancelled)
                except (OSError, ValueError, UnicodeError):
                    self.disconnect()
                    raise
                reads = dict(READS)
                reads['roomSetpoint'] = TARGETS[self.settings.target][0]
                if result.simulator:
                    reads.update(roomMeasuredTemp='getProbeRoomTemp', dhwSetpoint='getTempWWsoll')
                if result.live_identity and self.settings.live_writes:
                    reads['dhwSetpoint'] = 'getTempWWsoll'
                for key, command in reads.items():
                    try:
                        response = self._exchange(command, cancelled)
                    except (OSError, ValueError, UnicodeError):
                        # Framing/transport failure: never send more commands on this stream.
                        self.disconnect()
                        raise
                    try:
                        result.values[key] = temperature(response)
                        if on_progress is not None:
                            on_progress(result)
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


    def write_setpoint(self, target, value, cancelled=lambda: False):
        """Fresh endpoint identity, explicit live opt-in, one setter and readback; no retries."""
        if target not in TARGETS:
            raise ValueError('Unknown target')
        number = float(value)
        low, high = (10, 60) if target == 'dhw' else (3, 37)
        if not math.isfinite(number) or not number.is_integer() or not low <= number <= high:
            raise ValueError('Target must be a whole degree from %s to %s' % (low, high))
        try:
            if self.sock is None:
                self.sock = socket.create_connection((self.settings.host, self.settings.port), min(5, self.settings.timeout))
                self._frame(cancelled)
            # Check on this exact connection immediately before the one permitted write.
            identity = self._exchange('device', cancelled)
            if identity != SIMULATOR_ID:
                if not self.settings.live_writes or identity != LIVE_ID or target not in LIVE_TARGETS:
                    raise PermissionError('Live writes require opt-in, verified KO2B identity and an allowed target')
                # Single-byte reads can mistake an ENQ byte for a plausible target.
                # Require a fresh complete snapshot, including multi-byte temperatures.
                snapshot = self.poll(cancelled)
                required = set(READS) | {'dhwSetpoint'}
                if (not snapshot.live_identity or snapshot.errors or snapshot.release_error
                        or not required.issubset(snapshot.values)):
                    raise PermissionError('Live write blocked: fresh complete readings are required')
                current = snapshot.values['dhwSetpoint' if target == 'dhw' else 'roomSetpoint']
                if not low <= current <= high:
                    raise PermissionError('Live write blocked: existing target is outside allowed bounds')
                if self._exchange('device', cancelled) != LIVE_ID:
                    raise PermissionError('Controller identity changed before write')
            if cancelled():
                raise InterruptedError('Cancelled before write')
            read, setter = TARGETS[target]
            self.sock.settimeout(self.settings.timeout)
            self.sock.sendall(('%s %d\n' % (setter, number)).encode('ascii'))
            if self._frame(cancelled) != 'OK':
                raise ValueError('Setter did not return OK; result uncertain, not retried')
            actual = temperature(self._exchange(read, cancelled))
            if actual != number:
                raise ValueError('Setpoint readback mismatch; result uncertain, not retried')
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
        self.startup_failures = 0
        self.startup_complete = False

    def configure(self, settings):
        if settings != self.settings:
            self.close()
            self.settings = settings
            self.startup_failures = 0
            self.startup_complete = False
            self.due = self.clock()

    def request_poll(self):
        # Called only by the worker; repeated queued refresh requests coalesce.
        self.requested = True

    def tick(self, cancelled=lambda: False, on_progress=None):
        if (self.settings is None or cancelled()
                or (not self.requested and (not self.settings.enabled or self.clock() < self.due))):
            return None
        if self.client is None:
            self.client = self.client_factory(self.settings)
        self.requested = False
        result = (self.client.poll(cancelled) if on_progress is None
                  else self.client.poll(cancelled, on_progress))
        complete = (set(READS).issubset(result.values) and not result.errors
                    and not result.release_error)
        delay = self.settings.interval
        if complete:
            self.startup_complete = True
        elif not self.startup_complete:
            self.startup_failures += 1
            if self.settings.enabled and self.startup_failures <= 3:
                delay = 5
        # Delays start after completion: never overlap or retry setters.
        self.due = self.clock() + delay
        return result

    def write_setpoint(self, target, value, cancelled=lambda: False):
        if self.settings is None or not self.settings.enabled:
            raise PermissionError('Polling must be enabled to use setpoint controls')
        if self.client is None:
            self.client = self.client_factory(self.settings)
        actual = self.client.write_setpoint(target, value, cancelled)
        self.due = self.clock()
        return actual

    def close(self):
        self.requested = False
        if self.client is not None:
            self.client.disconnect()
        self.client = None
