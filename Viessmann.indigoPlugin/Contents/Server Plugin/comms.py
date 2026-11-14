"""Single-owner vcontrold polling and explicitly authorized setpoints; independent of Indigo."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
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
    health_interval: int = 30
    fault_interval: int = 60

    def __post_init__(self):
        if self.target not in ('standard', 'reduced', 'party'):
            raise ValueError('Invalid room target')
        if not self.host or any(c.isspace() for c in self.host):
            raise ValueError('A hostname or IP address is required')
        for value, low, high in ((self.port, 1, 65535), (self.interval, 30, 86400),
                                 (self.timeout, 1, 60), (self.health_interval, 10, 86400), (self.fault_interval, 10, 86400)):
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
    # Current fault interpretation; KO2B relay mapping is an owner-approved trial.
    # History alone never establishes an active fault.
    verified_active_fault_code: str = ''
    active_fault_known: bool = False
    system_time: str = ''
    health_ok: bool = False
    health_error: str = ''
    health_checked: str = ''
    health_only: bool = False
    fault_only: bool = False
    fault_record: str = ''
    relay_status: str = ''
    fault_checked: str = ''
    fault_error: str = ''
    production_status: dict | None = None
    production_status_raw: str = ''
    production_status_checked: str = ''
    production_status_error: str = ''
    burner_status: str = ''
    burner_checked: str = ''
    burner_output: float | None = None
    burner_output_status: int | None = None
    burner_output_raw: str = ''
    burner_output_checked: str = ''
    burner_output_error: str = ''


class Client:
    """Persistent TCP and Optolink, one serialized owner. Not thread-safe by design."""
    def __init__(self, settings):
        self.settings = settings
        self.sock = None
        self.buffer = b''
        self.last_health = None
        self.last_system_time = ''
        self.last_health_checked = ''

    def disconnect(self):
        if self.sock is not None:
            self.sock.close()
        self.sock = None
        self.buffer = b''
        self.last_health = None
        self.last_system_time = ''
        self.last_health_checked = ''

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
        allowed = set(READS.values()) | {v[0] for v in TARGETS.values()} | {'getProbeRoomTemp', 'getSystemTime', 'getError0', 'getProbeRelayStatus', 'getProbeProductionStatus', 'getProbeBurner1', 'getProbeOutputStatus', 'device', 'close'}
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

    def _connect(self, cancelled):
        if self.sock is None:
            self.sock = socket.create_connection(
                (self.settings.host, self.settings.port), min(5, self.settings.timeout))
            self._frame(cancelled)

    def _ensure_health(self, result, cancelled, force=False):
        self._connect(cancelled)
        result.tcp_available = True
        identity = self._exchange('device', cancelled)
        result.simulator = identity == SIMULATOR_ID
        result.live_identity = identity == LIVE_ID
        if (force or self.last_health is None
                or time.monotonic() - self.last_health >= self.settings.health_interval):
            text = self._exchange('getSystemTime', cancelled)
            if not re.fullmatch(r'20[0-9]{2}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}[+-][0-9]{4}', text):
                raise ValueError('Invalid controller time: ' + text[:160])
            datetime.strptime(text, '%Y-%m-%dT%H:%M:%S%z')
            self.last_health = time.monotonic()
            self.last_system_time = text
            self.last_health_checked = datetime.now(timezone.utc).isoformat(timespec='seconds')
        result.health_ok = True
        result.system_time = self.last_system_time
        result.health_checked = self.last_health_checked
        return identity

    def _health_failure(self, result, exc, cancelled):
        result.health_error = str(exc)
        self.disconnect()  # release held serial ownership before any raw diagnostic
        if cancelled() or not result.tcp_available or not self.settings.activity_probe:
            return
        try:
            self._connect(cancelled)
            identity = self._exchange('device', cancelled)
            self._activity_probe(result, identity, cancelled)
        except (OSError, ValueError, UnicodeError) as diagnostic:
            result.optical_error = str(diagnostic)
        finally:
            self.disconnect()  # raw diagnostics never retain an ambiguous session

    def health(self, cancelled=lambda: False):
        result = Result(health_only=True)
        try:
            self._ensure_health(result, cancelled, force=True)
        except (OSError, ValueError, UnicodeError) as exc:
            self._health_failure(result, exc, cancelled)
        return result

    def fault(self, cancelled=lambda: False):
        result = Result(health_only=True, fault_only=True)
        try:
            self._ensure_health(result, cancelled)
        except (OSError, ValueError, UnicodeError) as exc:
            result.fault_error = str(exc)
            result.health_error = str(exc)
            self.disconnect()
            return result
        errors = []
        for command, attribute in [('getError0', 'fault_record'), ('getProbeRelayStatus', 'relay_status'), ('getProbeProductionStatus', 'production_status'), ('getProbeBurner1', 'burner_status'), ('getProbeOutputStatus', 'burner_output')]:
            try:
                text = self._exchange(command, cancelled)
            except (OSError, ValueError, UnicodeError) as exc:
                errors.append(str(exc))
                self.disconnect()
                break
            try:
                if attribute == 'burner_output':
                    result.burner_output_raw = text
                elif attribute == 'production_status':
                    result.production_status_raw = text
                if not text or 'ERR' in text or 'UNKNOWN' in text or 'Error executing' in text:
                    raise ValueError('Fault sampling failed: ' + text[:160])
                if attribute == 'relay_status':
                    if not re.fullmatch(r'[0-9A-Fa-f]{2} [0-9A-Fa-f]{2}', text):
                        raise ValueError('Invalid relay status: ' + text[:160])
                    if bytes.fromhex(text) == b'\x05\x05':
                        raise ValueError('Suspect synchronization bytes in relay status: 05 05')
                elif attribute == 'production_status':
                    if not re.fullmatch(r'[0-9A-Fa-f]{2}(?: [0-9A-Fa-f]{2}){3}', text):
                        raise ValueError('Invalid four-byte production status: ' + text[:160])
                    raw = bytes.fromhex(text)
                    if raw in (b'\x05' * 4, b'\xff' * 4):
                        raise ValueError('Unavailable or suspect production status: ' + text[:160])
                    # KO2B catalog: MSB-first bit positions 21, 23, 20, 14.
                    # These are Vitotronic production flags, not Siemens flame proof.
                    text = {'productionFault': bool(raw[2] & 0x04),
                            'productionHardBlock': bool(raw[2] & 0x01),
                            'productionSpecialOperation': bool(raw[2] & 0x08),
                            'productionStorageCharging': bool(raw[1] & 0x02)}
                    result.production_status_checked = datetime.now(timezone.utc).isoformat(timespec='seconds')
                elif attribute == 'burner_status':
                    if text not in ('00', '01'):
                        raise ValueError('Invalid burner activity: ' + text[:160])
                    result.burner_checked = datetime.now(timezone.utc).isoformat(timespec='seconds')
                elif attribute == 'burner_output':
                    if not re.fullmatch(r'[0-9A-Fa-f]{2} [0-9A-Fa-f]{2}', text):
                        raise ValueError('Invalid two-byte output/status: ' + text[:160])
                    if bytes.fromhex(text) == b'\x05\x05':
                        raise ValueError('Suspect synchronization bytes in output/status: 05 05')
                    value, status = bytes.fromhex(text)
                    if value > 200:
                        raise ValueError('Invalid burner output byte: ' + text[:160])
                    # Status is preserved as a byte, not assumed to prove flame.
                    result.burner_output_status = status
                    text = value / 2.0
                    result.burner_output_checked = datetime.now(timezone.utc).isoformat(timespec='seconds')
                elif not re.search(r'\([0-9A-Fa-f]{2}\)$', text):
                    raise ValueError('Invalid error history: ' + text[:160])
                setattr(result, attribute, text)
            except ValueError as exc:
                errors.append(str(exc))
                if attribute == 'burner_output':
                    result.burner_output_error = str(exc)
                elif attribute == 'production_status':
                    result.production_status_error = str(exc)
        result.fault_error = '; '.join(errors)
        if result.relay_status and (result.live_identity or result.simulator):
            # Provisional mapping observed across D1 and owner-confirmed recovery.
            # Scope strictly to KO2B/209F, and use only first-byte mask 0x01.
            result.active_fault_known = True
            if bytes.fromhex(result.relay_status)[0] & 0x01:
                match = re.search(r'\(([0-9A-Fa-f]{2})\)$', result.fault_record)
                code = match.group(1).upper() if match else ''
                result.verified_active_fault_code = code if code and code != '00' else 'Unknown'
        if result.relay_status or result.fault_record:
            result.fault_checked = datetime.now(timezone.utc).isoformat(timespec='seconds')
        return result

    def poll(self, cancelled=lambda: False, on_progress=None):
        result = Result()
        try:
            self._ensure_health(result, cancelled)
        except (OSError, ValueError, UnicodeError) as exc:
            self._health_failure(result, exc, cancelled)
            for key in READS:
                result.errors[key] = str(exc) if result.tcp_available else (
                    f'Connect to {self.settings.host}:{self.settings.port} failed: {exc}')
            return result
        reads = dict(READS)
        reads['roomSetpoint'] = TARGETS[self.settings.target][0]
        if result.simulator or result.live_identity:
            reads['roomMeasuredTemp'] = 'getProbeRoomTemp'
        if result.simulator:
            reads['dhwSetpoint'] = 'getTempWWsoll'
        if result.live_identity and self.settings.live_writes:
            reads['dhwSetpoint'] = 'getTempWWsoll'
        for key, command in reads.items():
            try:
                try:
                    response = self._exchange(command, cancelled)
                except ValueError:
                    self.disconnect()
                    raise
                result.values[key] = temperature(response)
                if on_progress is not None:
                    on_progress(result)
            except ValueError as exc:
                result.errors[key] = str(exc)
                # A framed decoder error does not invalidate other datapoints.
                if self.sock is None:
                    break
            except (OSError, UnicodeError) as exc:
                self.disconnect()
                for missing in reads:
                    if missing not in result.values and missing not in result.errors:
                        result.errors[missing] = str(exc)
                break
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
            self._connect(cancelled)
            identity = self._exchange('device', cancelled)
            if identity != SIMULATOR_ID:
                if not self.settings.live_writes or identity != LIVE_ID or target not in LIVE_TARGETS:
                    raise PermissionError('Live writes require opt-in, verified KO2B identity and an allowed target')
            # Reuse a recent clock check on this socket; no full pre-write poll.
            health = Result()
            checked_identity = self._ensure_health(health, cancelled)
            if checked_identity != identity:
                raise PermissionError('Controller identity changed before write')
            read, setter = TARGETS[target]
            current = temperature(self._exchange(read, cancelled))
            if not low <= current <= high:
                raise PermissionError('Existing target is outside allowed bounds')
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
        self.health_due = 0
        self.fault_due = 0

    def configure(self, settings):
        if settings != self.settings:
            self.close()
            self.settings = settings
            self.startup_failures = 0
            self.startup_complete = False
            self.due = self.clock()
            self.health_due = self.clock()
            self.fault_due = self.clock()

    def request_poll(self):
        # Called only by the worker; repeated queued refresh requests coalesce.
        self.requested = True

    def tick(self, cancelled=lambda: False, on_progress=None):
        if (self.settings is None or cancelled()
                or (not self.requested and (not self.settings.enabled
                    or self.clock() < min(self.due, self.health_due, self.fault_due)))):
            return None
        if self.client is None:
            self.client = self.client_factory(self.settings)
        if not self.requested and self.clock() < self.due and self.clock() >= self.fault_due:
            result = self.client.fault(cancelled)
            self.fault_due = self.clock() + self.settings.fault_interval
            if result.health_ok:
                self.health_due = self.clock() + self.settings.health_interval
            return result
        if not self.requested and self.clock() < self.due:
            result = self.client.health(cancelled)
            self.health_due = self.clock() + self.settings.health_interval
            return result
        self.requested = False
        result = (self.client.poll(cancelled) if on_progress is None
                  else self.client.poll(cancelled, on_progress))
        self.health_due = self.clock() + self.settings.health_interval
        if self.fault_due <= self.clock():
            # Full readings and fault reads are separate serialized work items.
            self.fault_due = self.clock()
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
        return actual

    def close(self):
        self.requested = False
        if self.client is not None:
            self.client.disconnect()
        self.client = None
