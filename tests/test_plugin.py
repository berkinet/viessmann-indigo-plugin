"""Synthetic protocol fixtures, not evidence of live heater behavior."""
import importlib.util
from pathlib import Path
import socketserver
import sys
import threading
import time
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Viessmann.indigoPlugin/Contents/Server Plugin'))
from comms import Client, Manager, Settings, Result, READS, temperature


def readings(*values):
    return dict(zip(READS, values), roomMeasuredTemp=20.7)


class FixtureServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, answers=None, stall=False, close_reply=None):
        self.commands = []
        self.connections = 0
        self.answers = answers or ['27.4 C', '0 C', '19.0', '-2.5 C']
        self.stall = stall
        self.close_reply = close_reply
        self.activity_reply = 'Result: 05'
        self.clock_reply = '2026-11-13T14:37:23+0000'
        self.targets = {'getRoomTempSP': '19', 'getTempWWsoll': '50'}
        self.output_reply = '4B 01'
        self.production_reply = '00 00 00 00'
        self.burner_reply = '01'
        self.relay_reply = '83 80'
        self.error_reply = '2026-11-13T14:30:08+0000 Burner Fault (D1)'
        self.setter_reply = 'OK'
        self.apply_setter = True
        self.identity = "V200KO2B (ID=209F) (Protocol=KW2)"
        owner = self

        class Handler(socketserver.StreamRequestHandler):
            def handle(self):
                owner.connections += 1
                # Fragment prompt and responses across arbitrary TCP packet boundaries.
                try:
                    self.wfile.write(b'vc'); self.wfile.flush()
                    self.wfile.write(b'trld> '); self.wfile.flush()
                    while True:
                        data = self.rfile.readline()
                        if not data:
                            return
                        command = data.decode().strip()
                        owner.commands.append(command)
                        if owner.stall:
                            time.sleep(1.2)
                            return
                        if command == 'raw':
                            # A raw script is collected before execution, with no
                            # intermediate vctrld prompt.
                            for expected in ('RECV 1', 'END'):
                                line = self.rfile.readline().decode().strip()
                                owner.commands.append(line)
                                if line != expected:
                                    raise AssertionError(line)
                            if owner.activity_reply is None:
                                return  # vcontrold exits child on raw read timeout
                            reply = owner.activity_reply + '\nvctrld> '
                        elif command == 'getProbeOutputStatus':
                            reply = owner.output_reply + '\nvctrld> '
                        elif command == 'getProbeProductionStatus':
                            reply = owner.production_reply + '\nvctrld> '
                        elif command == 'getProbeBurner1':
                            reply = owner.burner_reply + '\nvctrld> '
                        elif command == 'getError0':
                            reply = owner.error_reply + '\nvctrld> '
                        elif command == 'getProbeRelayStatus':
                            reply = owner.relay_reply + '\nvctrld> '
                        elif command == 'getProbeRoomTemp':
                            reply = '20.7 C\nvctrld> '
                        elif command == 'getSystemTime':
                            reply = owner.clock_reply + '\nvctrld> '
                        elif command == 'device':
                            reply = owner.identity + '\nvctrld> '
                        elif command.startswith(('setTempRaumNorSollM1 ', 'setTempWWsoll ')):
                            setter, value = command.split()
                            read = 'getRoomTempSP' if setter == 'setTempRaumNorSollM1' else 'getTempWWsoll'
                            if owner.apply_setter: owner.targets[read] = value
                            reply = owner.setter_reply + '\nvctrld> '
                        elif command == 'getTempWWsoll' or (command == 'getRoomTempSP' and any(c.startswith('setTempRaumNorSollM1 ') for c in owner.commands)):
                            reply = owner.targets[command] + '\nvctrld> '
                        elif command == 'close':
                            reply = (owner.close_reply or '/dev/test closed') + '\nvctrld> '
                        else:
                            reply = owner.answers[list(READS.values()).index(command)] + '\nvctrld> '
                        raw = reply.encode()
                        self.wfile.write(raw[:3]); self.wfile.flush()
                        self.wfile.write(raw[3:]); self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    return
        super().__init__(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.serve_forever, daemon=True)
        self.thread.start()

    def settings(self, **kw):
        return Settings('127.0.0.1', port=self.server_address[1], enabled=True, **kw)

    def stop(self):
        self.shutdown(); self.server_close(); self.thread.join(2)


class TransportTests(unittest.TestCase):
    def test_persistent_socket_and_optical_ownership_without_per_cycle_close(self):
        server = FixtureServer()
        client = Client(server.settings())
        try:
            for _ in range(2):
                result = client.poll()
                self.assertEqual(result.values, readings(27.4, 0, 19, -2.5))
                self.assertFalse(result.errors)
                self.assertFalse(result.release_error)
            self.assertEqual(server.connections, 1)
            self.assertEqual(server.commands, ['device', 'getSystemTime'] + list(READS.values()) + ['getProbeRoomTemp', 'device'] + list(READS.values()) + ['getProbeRoomTemp'])
            self.assertTrue(result.health_ok)
            self.assertNotIn('close', server.commands)
        finally:
            client.disconnect(); server.stop()

    def test_activity_is_independent_of_successful_register_reads(self):
        server = FixtureServer(['UNKNOWN'] * 4)
        server.clock_reply = 'UNKNOWN'
        client = Client(server.settings())
        try:
            result = client.poll()
            self.assertEqual(result.optical_activity, 'Detected')
            self.assertTrue(result.optical_checked)
            self.assertFalse(result.values)
            self.assertEqual(len(result.errors), 4)
            self.assertFalse(any(c.startswith(('SEND', 'set')) for c in server.commands))
        finally:
            client.disconnect(); server.stop()

    def test_silent_fallback_disconnect_reconnects_on_next_health_check(self):
        server = FixtureServer()
        server.activity_reply = None
        server.clock_reply = 'UNKNOWN'
        client = Client(server.settings())
        try:
            result = client.poll()
            self.assertEqual(result.optical_activity, 'Not detected')
            self.assertIn('disconnected', result.optical_error)
            self.assertFalse(result.values)
            self.assertIsNone(client.sock)
            server.clock_reply = '2026-11-13T14:37:24+0000'
            self.assertTrue(client.health().health_ok)
            self.assertEqual(server.connections, 3)
            self.assertNotIn('close', server.commands)
        finally:
            client.disconnect(); server.stop()

    def test_unexpected_byte_and_protocol_gating(self):
        server = FixtureServer()
        client = Client(server.settings())
        try:
            server.clock_reply = 'UNKNOWN'
            server.activity_reply = 'Result: FF'
            self.assertEqual(client.poll().optical_activity, 'Unexpected byte')
            before = server.commands.count('raw')
            server.identity = 'Other (ID=1234) (Protocol=P300)'
            result = client.poll()
            self.assertEqual(result.optical_activity, 'Unsupported')
            self.assertFalse(result.optical_checked)
            self.assertEqual(server.commands.count('raw'), before)
        finally:
            client.disconnect(); server.stop()

    def test_cancelled_probe_sends_nothing_and_raw_is_not_a_general_command(self):
        client = Client(Settings('localhost'))
        result = Result()
        with self.assertRaises(InterruptedError):
            client._activity_probe(result, 'V200KO2B (ID=209F) (Protocol=KW2)', lambda: True)
        self.assertFalse(result.optical_checked)
        with self.assertRaises(ValueError):
            client._exchange('raw', lambda: False)

    def test_disabled_probe_does_not_send_raw(self):
        server = FixtureServer()
        client = Client(server.settings(activity_probe=False))
        try:
            self.assertTrue(client.poll().health_ok)
            self.assertNotIn('raw', server.commands)
        finally:
            client.disconnect(); server.stop()

    def test_error_text_never_becomes_reading_and_stream_stays_aligned(self):
        server = FixtureServer(['ERR: timeout after 5 seconds\nError executing getBoilerTemp',
                                'UNKNOWN', '21', '-4 C'])
        client = Client(server.settings())
        try:
            result = client.poll()
            self.assertEqual(set(result.errors), {'boilerTemp', 'outsideTemp'})
            self.assertEqual(result.values, {'roomSetpoint': 21, 'warmWaterTemp': -4, 'roomMeasuredTemp': 20.7})
            self.assertNotIn('close', server.commands)
        finally:
            client.disconnect(); server.stop()

    def test_timeout_disconnects_and_next_cycle_reconnects(self):
        server = FixtureServer(stall=True)
        client = Client(server.settings(timeout=1, activity_probe=False))
        try:
            start = time.monotonic()
            result = client.poll()
            self.assertLess(time.monotonic() - start, 2)
            self.assertEqual(set(result.errors), set(READS))
            self.assertIsNone(client.sock)
            self.assertEqual(server.commands, ['device'])
            server.stall = False
            self.assertEqual(len(client.poll().values), 5)
            self.assertEqual(server.connections, 2)
        finally:
            client.disconnect(); server.stop()

    def test_invalid_clock_blocks_live_setter_without_full_poll(self):
        server = FixtureServer()
        server.clock_reply = '2005-05-05T05:05:05+0000 junk'
        client = Client(server.settings(live_writes=True, activity_probe=False))
        try:
            with self.assertRaisesRegex(ValueError, 'controller time'):
                client.write_setpoint('standard', 21)
            self.assertFalse(any(c.startswith('set') for c in server.commands))
            self.assertIsNone(client.sock)
            self.assertNotIn('getBoilerTemp', server.commands)
        finally:
            client.disconnect(); server.stop()

    def test_health_reuses_socket_and_invalid_time_never_confirms_health(self):
        server = FixtureServer()
        client = Client(server.settings(activity_probe=False))
        try:
            self.assertTrue(client.health().health_ok)
            server.clock_reply = '2026-11-13T14:37:24+0000'
            self.assertTrue(client.health().health_ok)
            self.assertEqual(server.connections, 1)
            self.assertNotIn('raw', server.commands)
            self.assertNotIn('close', server.commands)
            self.assertNotIn('getBoilerTemp', server.commands)
            server.clock_reply = '2026-02-31T14:37:24+0000'
            self.assertFalse(client.health().health_ok)
            self.assertIsNone(client.sock)
            server.clock_reply = '2026-11-13T14:37:25+0000'
            self.assertTrue(client.health().health_ok)
            self.assertEqual(server.connections, 2)
        finally:
            client.disconnect(); server.stop()

    def test_relay_flag_establishes_fault_and_clears_with_history_retained(self):
        server = FixtureServer()
        client = Client(server.settings())
        try:
            result = client.fault()
            self.assertTrue(result.health_ok)
            self.assertIn('(D1)', result.fault_record)
            self.assertEqual(result.relay_status, '83 80')
            self.assertEqual(result.burner_status, '01')
            server.burner_reply = '05'
            bad_burner = client.fault()
            self.assertFalse(bad_burner.burner_status)
            self.assertIn('burner activity', bad_burner.fault_error)
            server.burner_reply = '01'
            self.assertEqual(result.verified_active_fault_code, 'D1')
            self.assertTrue(result.active_fault_known)
            server.relay_reply = '82 80'
            cleared = client.fault()
            self.assertTrue(cleared.active_fault_known)
            self.assertFalse(cleared.verified_active_fault_code)
            self.assertIn('(D1)', cleared.fault_record)
            server.relay_reply = '05 05'
            invalid = client.fault()
            self.assertFalse(invalid.active_fault_known)
            self.assertIn('synchronization', invalid.fault_error)
            server.relay_reply = '83 20'
            server.error_reply = 'ERR: history failed'
            unknown = client.fault()
            self.assertTrue(unknown.active_fault_known)
            self.assertEqual(unknown.verified_active_fault_code, 'Unknown')
            server.identity = 'Other (ID=1234) (Protocol=KW2)'
            self.assertFalse(client.fault().active_fault_known)
            self.assertNotIn('close', server.commands)
        finally:
            client.disconnect(); server.stop()

    def test_output_percentage_accepts_zero_and_rejects_errors_without_losing_relay(self):
        server = FixtureServer()
        client = Client(server.settings())
        try:
            self.assertEqual(client.fault().burner_output, 37.5)
            server.output_reply = 'C8 01'
            result = client.fault()
            self.assertEqual(result.burner_output, 100)
            self.assertEqual(result.burner_output_status, 1)
            self.assertEqual(result.burner_output_raw, 'C8 01')
            server.output_reply = '01 A7'
            result = client.fault()
            self.assertEqual(result.burner_output, 0.5)
            self.assertEqual(result.burner_output_status, 167)  # Unknown status stays diagnostic.
            server.output_reply = '00 00'
            self.assertEqual(client.fault().burner_output, 0)
            for reply in ('UNKNOWN', 'ERR: read 5 failed', 'FF 01', 'C9 00', '05 05', '05 05 05', '01', '01 00 00', 'GG 01', '37.5 %'):
                server.output_reply = reply
                result = client.fault()
                self.assertIsNone(result.burner_output)
                self.assertTrue(result.burner_output_error)
                self.assertTrue(result.active_fault_known)
        finally:
            client.disconnect(); server.stop()

    def test_production_status_extracts_each_catalog_bit_from_full_block(self):
        server = FixtureServer()
        client = Client(server.settings())
        keys = ('productionFault', 'productionHardBlock', 'productionSpecialOperation', 'productionStorageCharging')
        try:
            for reply, active in [('00 00 04 00', {keys[0]}), ('00 00 01 00', {keys[1]}),
                                  ('00 00 08 00', {keys[2]}), ('00 02 00 00', {keys[3]}),
                                  ('00 02 0D 00', set(keys)), ('04 00 00 00', set()),
                                  ('00 00 00 00', set())]:
                server.production_reply = reply
                result = client.fault()
                self.assertEqual({key for key, value in result.production_status.items() if value}, active)
                self.assertEqual(result.production_status_raw, reply)
                self.assertTrue(result.production_status_checked)
            for reply in ('00', '00 00 00', '00 00 00 00 00', 'FF FF FF FF', '05 05 05 05', 'ERR: timeout', 'UNKNOWN'):
                server.production_reply = reply
                result = client.fault()
                self.assertIsNone(result.production_status)
                self.assertTrue(result.production_status_error)
                self.assertEqual(result.production_status_raw, reply)
                self.assertEqual(result.burner_output, 37.5)
        finally:
            client.disconnect(); server.stop()

    def test_physical_identity_blocks_writes(self):
        server = FixtureServer()
        client = Client(server.settings())
        try:
            with self.assertRaises(PermissionError):
                client.write_setpoint('standard', 21)
            self.assertEqual(server.commands, ['device'])
            self.assertIsNone(client.sock)
            for target, value in [('standard', 38), ('standard', 20.5), ('dhw', 9), ('bogus', 20)]:
                with self.subTest(target=target, value=value), self.assertRaises(ValueError):
                    client.write_setpoint(target, value)
            self.assertEqual(server.commands, ['device'])
        finally:
            client.disconnect(); server.stop()

    def test_live_write_opt_in_identity_target_and_readback(self):
        server = FixtureServer()
        client = Client(server.settings(live_writes=True))
        try:
            self.assertEqual(client.write_setpoint('standard', 21), 21)
            self.assertEqual(client.write_setpoint('dhw', 51), 51)
            for target in ('reduced', 'party'):
                with self.assertRaises(PermissionError): client.write_setpoint(target, 20)
            server.identity = 'V200KW2 (ID=2098) (Protocol=KW2)'
            with self.assertRaises(PermissionError): client.write_setpoint('dhw', 50)
            server.identity = 'V200KO2B (ID=209F) (Protocol=KW2)'
            # A single target read and recent clock health replace the full pre-write snapshot.
            self.assertNotIn('getBoilerTemp', server.commands)
            server.apply_setter = False
            before = len(server.commands)
            with self.assertRaisesRegex(ValueError, 'mismatch'):
                client.write_setpoint('dhw', 52)
            self.assertEqual(server.commands[before:].count('setTempWWsoll 52'), 1)
            self.assertIsNone(client.sock)
            server.setter_reply = 'ERR: failed'
            with self.assertRaisesRegex(ValueError, 'uncertain'):
                client.write_setpoint('dhw', 52)
        finally:
            client.disconnect(); server.stop()

    def test_strict_parse_and_read_only_allowlist(self):
        for text in ('ERR: 5', 'UNKNOWN', 'nan', '28 C\nextra', '27 boiler'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                temperature(text)
        client = Client(Settings('localhost'))
        with self.assertRaises(ValueError):
            client._exchange('setTempWWsoll 50', lambda: False)

    def test_progress_callback_runs_before_later_reads_and_close(self):
        server = FixtureServer()
        client = Client(server.settings())
        seen = []
        try:
            result = client.poll(on_progress=lambda partial: seen.append((set(partial.values), list(server.commands))))
            self.assertEqual(len(seen), 5)
            self.assertEqual(seen[0][0], {'boilerTemp'})
            self.assertNotIn('getOutsideTemp', seen[0][1])
            self.assertTrue(all('close' not in commands for _, commands in seen))
            self.assertFalse(result.release_error)
        finally:
            client.disconnect(); server.stop()

    def test_cancellation_closes_session(self):
        server = FixtureServer()
        client = Client(server.settings())
        try:
            result = client.poll(lambda: True)
            self.assertIsNone(client.sock)
            self.assertEqual(set(result.errors), set(READS))
            self.assertEqual(server.commands, [])
        finally:
            client.disconnect(); server.stop()


class SchedulingTests(unittest.TestCase):
    def test_disabled_interval_changes_and_no_catchup(self):
        clock = [0]
        instances = []
        class Fake:
            def __init__(self, settings):
                self.calls = 0; self.closed = False; instances.append(self)
            def poll(self, cancelled):
                self.calls += 1; clock[0] += 20; return Result(values=dict.fromkeys(READS, 20))
            def disconnect(self): self.closed = True
        manager = Manager(clock=lambda: clock[0], client_factory=Fake)
        manager.configure(Settings('localhost'))
        self.assertIsNone(manager.tick())
        self.assertEqual(instances, [])
        manager.configure(Settings('localhost', enabled=True, health_interval=86400, fault_interval=86400))
        self.assertIsNotNone(manager.tick())
        manager.fault_due = 86400
        clock[0] = 199
        self.assertIsNone(manager.tick())
        clock[0] = 200
        self.assertIsNotNone(manager.tick())
        self.assertEqual(len(instances), 1)
        manager.configure(Settings('localhost', interval=30, enabled=True, health_interval=86400, fault_interval=86400))
        self.assertTrue(instances[0].closed)
        self.assertIsNotNone(manager.tick())
        manager.close()
        self.assertTrue(instances[-1].closed)


    def test_startup_retries_are_bounded_and_stop_after_complete_snapshot(self):
        clock = [0]
        class Fake:
            def __init__(self, settings): self.good = False
            def poll(self, cancelled):
                clock[0] += 2
                return Result(values=dict.fromkeys(READS, 20)) if self.good else Result()
            def disconnect(self): pass
        manager = Manager(clock=lambda: clock[0], client_factory=Fake)
        manager.configure(Settings('localhost', enabled=True, health_interval=86400, fault_interval=86400))
        for attempt in range(4):
            self.assertIsNotNone(manager.tick())
            self.assertEqual(manager.due, clock[0] + (5 if attempt < 3 else 180))
            clock[0] = manager.due
            manager.fault_due = clock[0] + 86400
        manager.client.good = True
        manager.tick()
        self.assertTrue(manager.startup_complete)
        clock[0] = manager.due
        manager.client.good = False
        manager.fault_due = clock[0] + 86400
        manager.tick()
        self.assertEqual(manager.due, clock[0] + 180)
        manager.configure(Settings('other-host', enabled=True, health_interval=86400, fault_interval=86400))
        manager.tick()
        self.assertEqual(manager.due, clock[0] + 5)

    def test_health_checks_run_independently_without_starting_full_polls(self):
        clock = [0]
        calls = []
        class Fake:
            def __init__(self, settings): pass
            def poll(self, cancelled): calls.append('poll'); return Result(values=dict.fromkeys(READS, 20), health_ok=True)
            def health(self, cancelled): calls.append('health'); return Result(health_only=True, health_ok=True)
            def fault(self, cancelled): calls.append('fault'); return Result(health_only=True, fault_only=True, health_ok=True)
            def disconnect(self): calls.append('disconnect')
        manager = Manager(clock=lambda: clock[0], client_factory=Fake)
        manager.configure(Settings('localhost', enabled=True, interval=180, health_interval=30, fault_interval=90))
        manager.tick()
        self.assertTrue(manager.tick().fault_only)
        clock[0] = 29
        self.assertIsNone(manager.tick())
        clock[0] = 30
        self.assertTrue(manager.tick().health_only)
        self.assertEqual(manager.due, 180)
        clock[0] = 60
        manager.tick()
        clock[0] = 180
        manager.tick()
        self.assertEqual(calls, ['poll', 'fault', 'health', 'health', 'poll'])
        manager.configure(Settings('localhost', enabled=False))
        clock[0] = 1000
        self.assertIsNone(manager.tick())

    def test_manual_poll_coalesces_without_enabling_periodic_polling(self):
        calls = []
        class Fake:
            def __init__(self, settings): pass
            def poll(self, cancelled): calls.append(1); return Result()
            def disconnect(self): pass
        manager = Manager(clock=lambda: 100, client_factory=Fake)
        manager.configure(Settings('localhost', enabled=False))
        manager.request_poll(); manager.request_poll()
        self.assertIsNotNone(manager.tick())
        self.assertEqual(len(calls), 1)
        self.assertIsNone(manager.tick())
        self.assertFalse(manager.settings.enabled)
        manager.request_poll()
        manager.configure(Settings('other-host', enabled=False))
        self.assertIsNone(manager.tick())


# Minimal Indigo surface: verify value distribution and stale-data behavior offline.
class Device:
    def __init__(self, ident, kind, props):
        self.id, self.deviceTypeId, self.pluginProps = ident, kind, props
        self.pluginId = 'test'; self.name = kind; self.states = {}; self.error = None
    def updateStatesOnServer(self, updates):
        self.states.update({u['key']: u['value'] for u in updates})
    def setErrorStateOnServer(self, error): self.error = error
    def updateStateImageOnServer(self, selector): self.icon = selector
    def stateListOrDisplayStateIdChanged(self): pass
    def replacePluginPropsOnServer(self, props): self.pluginProps = dict(props)


class Devices(dict):
    def iter(self, plugin_id): return iter(self.values())


class AdapterTests(unittest.TestCase):
    def setUp(self):
        stub = types.ModuleType('indigo')
        class Base:
            def __init__(self, ident, *args): self.pluginId = ident; self.pluginPrefs = dict(args[-1])
        stub.kStateImageSel = types.SimpleNamespace(TemperatureSensor='temp', SensorTripped='fault', SensorOff='unknown', HvacHeating='heating', HvacOff='idle')
        stub.PluginBase = Base; stub.Dict = dict; stub.devices = Devices()
        stub.kUniversalAction = types.SimpleNamespace(RequestStatus=1)
        stub.kThermostatAction = types.SimpleNamespace(SetHeatSetpoint=1, IncreaseHeatSetpoint=2, DecreaseHeatSetpoint=3)
        self.previous = sys.modules.get('indigo'); sys.modules['indigo'] = stub
        spec = importlib.util.spec_from_file_location('plugin_under_test',
            ROOT / 'Viessmann.indigoPlugin/Contents/Server Plugin/plugin.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        self.plugin = module.Plugin('test', 'Test', '0', {})
        import logging
        self.plugin.logger = logging.getLogger('test')
        self.devices = stub.devices
        for d in (Device(1, 'viessmannSystem', {'host': 'localhost'}),
                  Device(2, 'viessmannHeater', {'systemId': '1'}),
                  Device(3, 'viessmannWaterHeater', {'systemId': '1'})):
            self.devices[d.id] = d; self.plugin.deviceStartComm(d)
        self.plugin._process_events(); self.plugin._configure()

    def tearDown(self):
        self.plugin.manager.close()
        if self.previous is None: sys.modules.pop('indigo', None)
        else: sys.modules['indigo'] = self.previous

    def test_distribution_partial_failure_and_disabled_invalidates(self):
        self.devices[1].pluginProps['pollingEnabled'] = True
        self.plugin._configure()
        self.plugin._publish(Result(readings(25, -3, 19, 30), tcp_available=True))
        self.assertEqual(self.devices[2].states['roomSetpoint'], 19)
        self.assertNotIn('roomTemp', self.devices[2].states)
        last = self.devices[3].states['lastSuccess']
        self.plugin._publish(Result({'boilerTemp': 26, 'outsideTemp': -4, 'roomSetpoint': 20, 'roomMeasuredTemp': 20.7},
                                    {'warmWaterTemp': 'UNKNOWN'}, True))
        self.assertFalse(self.devices[1].states['dataValid'])
        self.assertTrue(self.devices[2].states['dataValid'])
        self.assertEqual(self.devices[3].states['warmWaterTemp'], 30)
        self.assertFalse(self.devices[3].states['warmWaterTempValid'])
        self.assertEqual(self.devices[3].states['lastSuccess'], last)
        self.devices[1].pluginProps['pollingEnabled'] = False
        self.plugin._configure()
        self.assertTrue(all(not d.states['dataValid'] for d in self.devices.values()))

    def test_native_mapping_never_uses_setpoint_as_measured_temperature(self):
        values = readings(66, -3, 20, 46)
        values.update(roomMeasuredTemp=20.7, dhwSetpoint=50)
        self.plugin._publish(Result(values=values, tcp_available=True, simulator=True))
        heater, dhw = self.devices[2], self.devices[3]
        self.assertEqual(heater.states['setpointHeat'], 20)
        self.assertEqual(heater.states['temperatureInput1'], 20.7)
        self.assertEqual(dhw.states['setpointHeat'], 50)
        self.assertEqual(dhw.states['temperatureInput1'], 46)
        self.assertTrue(heater.pluginProps['SupportsHeatSetpoint'])
        self.assertFalse(heater.pluginProps['SupportsCoolSetpoint'])
        self.assertFalse(heater.pluginProps['SupportsHvacOperationMode'])
        self.devices[2].pluginProps['roomTarget'] = 'reduced'
        self.plugin._configure()
        self.assertEqual(self.plugin.manager.settings.target, 'reduced')
        self.plugin._publish(Result(values=readings(66, -3, 16, 46), tcp_available=True))
        self.assertFalse(heater.pluginProps['SupportsHeatSetpoint'])
        self.assertEqual(heater.pluginProps['NumTemperatureInputs'], 1)

    def test_icon_uses_pending_updates_and_output_failure_retains_value(self):
        dev = self.devices[1]
        before = dict(dev.states)
        self.plugin._update_state_icon(dev, [
            {'key': 'healthValid', 'value': True}, {'key': 'burnerOutputValid', 'value': True},
            {'key': 'burnerOutput', 'value': 100}, {'key': 'status', 'value': 'Online'}])
        self.assertEqual(dev.icon, 'heating')
        self.assertEqual(dev.states, before)
        self.plugin._publish(Result(health_only=True, fault_only=True, health_ok=True, tcp_available=True,
                                    burner_status='00', burner_output=0, burner_output_status=0, burner_output_raw='00 00',
                                    burner_output_checked='2026-11-13T15:00:00+00:00'))
        self.assertEqual(dev.states['burnerOutput'], 0)
        self.assertEqual(dev.states['burnerOutputStatus'], 0)
        self.assertTrue(dev.states['burnerOutputValid'])
        self.assertEqual(dev.icon, 'idle')
        self.plugin._publish(Result(health_only=True, fault_only=True, health_ok=True, tcp_available=True,
                                    burner_status='00', burner_output_error='read failed'))
        self.assertEqual(dev.states['burnerOutput'], 0)
        self.assertFalse(dev.states['burnerOutputValid'])
        self.assertEqual(dev.icon, 'unknown')

    def test_output_drives_icon_and_conflicting_enable_is_logged_once(self):
        dev = self.devices[1]
        dev.states.update(healthValid=True, burnerOutputValid=True, burnerStatusValid=True,
                          burnerOutput=100, burnerActive=False, status='Online')
        with self.assertLogs('test', level='ERROR') as captured:
            self.plugin._update_state_icon(dev)
            self.plugin._update_state_icon(dev)
        self.assertEqual(len(captured.output), 1)
        self.assertEqual(dev.icon, 'heating')
        dev.states.update(burnerOutput=0, burnerActive=True)
        self.plugin._update_state_icon(dev)
        self.assertEqual(dev.icon, 'idle')
        dev.states.update(burnerOutput=100, burnerOutputValid=False)
        self.plugin._update_state_icon(dev)
        self.assertEqual(dev.icon, 'unknown')
        dev.states['status'] = 'Error D1'
        self.plugin._update_state_icon(dev)
        self.assertEqual(dev.icon, 'fault')

    def test_production_flags_retain_values_on_failure_and_do_not_override_fault_display(self):
        dev = self.devices[1]
        self.plugin._publish(Result(health_only=True, fault_only=True, health_ok=True, tcp_available=True,
                                    production_status={'productionFault': True, 'productionHardBlock': False,
                                                       'productionSpecialOperation': False, 'productionStorageCharging': True},
                                    production_status_raw='00 02 04 00', production_status_checked='2026-11-14T12:00:00+00:00'))
        self.assertTrue(dev.states['productionFault'])
        self.assertTrue(dev.states['productionStatusValid'])
        self.assertEqual(dev.states['status'], 'Online')
        self.plugin._publish(Result(health_only=True, fault_only=True, health_ok=True, tcp_available=True,
                                    production_status_raw='FF FF FF FF', production_status_error='unavailable'))
        self.assertFalse(dev.states['productionStatusValid'])
        self.assertTrue(dev.states['productionFault'])
        self.assertEqual(dev.states['productionStatusUpdated'], '2026-11-14T12:00:00+00:00')
        self.plugin._unavailable(dev, 'Polling disabled')
        self.assertFalse(dev.states['productionStatusValid'])

    def test_child_icons_are_fixed_and_system_activity_is_separate_from_fault(self):
        self.assertEqual(self.devices[2].icon, 'temp')
        self.assertEqual(self.devices[3].icon, 'temp')
        active = Result(health_only=True, fault_only=True, tcp_available=True, health_ok=True,
                        active_fault_known=True, burner_status='01', burner_output=100, burner_checked='2026-11-13T15:00:00+00:00')
        self.plugin._publish(active)
        self.assertEqual(self.devices[1].icon, 'heating')
        self.plugin._publish(Result(health_only=True, tcp_available=True, health_ok=True))
        self.assertEqual(self.devices[1].icon, 'heating')
        self.plugin._publish(Result(health_only=True, fault_only=True, tcp_available=True, health_ok=True,
                                    active_fault_known=True, burner_status='00', burner_output=0))
        self.assertEqual(self.devices[1].icon, 'idle')
        self.plugin._publish(Result(health_only=True, fault_only=True, tcp_available=True, health_ok=True,
                                    active_fault_known=True, verified_active_fault_code='D1', burner_status='01'))
        self.assertEqual(self.devices[1].icon, 'fault')
        self.plugin._publish(Result(health_only=True, fault_only=True, tcp_available=True, health_ok=True,
                                    active_fault_known=True, fault_error='bad burner byte'))
        self.assertEqual(self.devices[1].icon, 'unknown')
        self.assertEqual(self.devices[2].icon, 'temp')
        self.assertEqual(self.devices[3].icon, 'temp')

    def test_relay_trial_display_changes_without_affecting_child_controls(self):
        self.plugin._publish(Result(values=readings(42, 10, 20, 52.9), tcp_available=True))
        children = {i: (dict(self.devices[i].states), dict(self.devices[i].pluginProps)) for i in (2, 3)}
        self.plugin._publish(Result(health_only=True, fault_only=True, tcp_available=True, health_ok=True,
                                    active_fault_known=True, verified_active_fault_code='D1', relay_status='83 20'))
        self.assertEqual(self.devices[1].states['status'], 'Error D1')
        self.plugin._publish(Result(health_only=True, fault_only=True, tcp_available=True, health_ok=True,
                                    fault_error='Suspect 05 05'))
        self.assertEqual(self.devices[1].states['status'], 'Error D1')
        self.assertIn('Unknown', self.devices[1].states['faultStatus'])
        self.plugin._publish(Result(health_only=True, fault_only=True, tcp_available=True, health_ok=True,
                                    active_fault_known=True, relay_status='82 20', fault_record='Stored D1 (D1)'))
        self.assertEqual(self.devices[1].states['status'], 'Online')
        self.assertIsNone(self.devices[1].error)
        self.assertIn('Clear', self.devices[1].states['faultStatus'])
        for ident in (2, 3):
            self.assertEqual((self.devices[ident].states, self.devices[ident].pluginProps), children[ident])

    def test_clock_success_advances_only_system_last_success_even_with_fault(self):
        system = self.devices[1]
        system.states['lastSuccess'] = '2026-11-13T13:00:00+00:00'
        children = {ident: dict(self.devices[ident].states) for ident in (2, 3)}
        self.plugin._publish(Result(health_only=True, tcp_available=True, health_ok=True,
                                    health_checked='2026-11-13T14:00:00+00:00',
                                    active_fault_known=True, verified_active_fault_code='D1'))
        self.assertEqual(system.states['lastSuccess'], '2026-11-13T14:00:00+00:00')
        self.assertEqual(system.states['status'], 'Error D1')
        for ident in (2, 3): self.assertEqual(self.devices[ident].states, children[ident])
        self.plugin._publish(Result(health_only=True, tcp_available=True, health_ok=True,
                                    health_checked='2026-11-13T13:30:00+00:00'))
        self.assertEqual(system.states['lastSuccess'], '2026-11-13T14:00:00+00:00')
        self.plugin._publish(Result(health_only=True, tcp_available=True, health_error='timeout'))
        self.assertEqual(system.states['lastSuccess'], '2026-11-13T14:00:00+00:00')
        self.plugin._publish(Result(tcp_available=True, health_ok=True, errors={'boilerTemp': 'timeout'},
                                    health_checked='2026-11-13T14:01:00+00:00'))
        self.assertEqual(system.states['lastSuccess'], '2026-11-13T14:01:00+00:00')
        self.assertFalse(system.states['dataValid'])

    def test_clock_health_does_not_change_readings_or_clear_established_fault(self):
        values = readings(42, 10, 20, 52.9)
        self.plugin._publish(Result(values=values, tcp_available=True, verified_active_fault_code='D1'))
        before = dict(self.devices[2].states)
        self.plugin._publish(Result(health_only=True, tcp_available=True, health_ok=True,
                                    system_time='2026-11-13T14:37:23+0000', health_checked='2026-11-13T13:48:17+00:00'))
        self.assertEqual(self.devices[1].states['status'], 'Error D1')
        self.assertEqual(self.devices[1].error, 'Error D1')
        self.assertTrue(self.devices[1].states['healthValid'])
        self.assertEqual(self.devices[2].states, before)
        self.plugin._publish(Result(values=values, tcp_available=True, health_ok=True))
        self.assertEqual(self.devices[1].states['status'], 'Error D1')
        self.plugin._publish(Result(health_only=True, tcp_available=True, health_ok=True, active_fault_known=True))
        self.assertEqual(self.devices[1].states['status'], 'Online')

    def test_child_progress_publishes_once_before_final_release_without_controls(self):
        published = set()
        result = Result(values={'boilerTemp': 66}, tcp_available=True)
        self.plugin._publish_progress(result, published)
        self.assertFalse(published)
        result.values['roomSetpoint'] = 20
        result.values['roomMeasuredTemp'] = 20.7
        self.plugin._publish_progress(result, published)
        self.assertEqual(published, {2})
        self.assertEqual(self.devices[2].states['temperatureInput1'], 20.7)
        self.assertEqual(self.devices[2].states['status'], 'Online')
        self.assertFalse(self.devices[2].pluginProps.get('SupportsHeatSetpoint', False))
        result.values['warmWaterTemp'] = 46
        self.plugin._publish_progress(result, published)
        self.assertEqual(published, {2, 3})
        self.assertEqual(self.devices[3].states['temperatureInput1'], 46)
        result.release_error = 'close failed'
        self.plugin._publish(result)
        self.assertIn('close failed', self.devices[2].states['lastError'])

    def test_early_readings_do_not_toggle_writable_capabilities_between_polls(self):
        self.plugin.pluginPrefs['liveWritesEnabled'] = True
        values = readings(42, 10, 20, 52.9)
        values['dhwSetpoint'] = 54
        full = Result(values=values, tcp_available=True, live_identity=True, health_ok=True)
        self.plugin._publish(full)
        changes = []
        for ident in (2, 3):
            dev = self.devices[ident]
            original = dev.replacePluginPropsOnServer
            def replace(props, ident=ident, original=original):
                changes.append(ident)
                original(props)
                # Model Indigo restarting communications on a property change.
                self.plugin.deviceStopComm(self.devices[ident])
                self.plugin.deviceStartComm(self.devices[ident])
            dev.replacePluginPropsOnServer = replace
        for _ in range(3):
            partial = Result(values={'boilerTemp': 42, 'roomSetpoint': 20,
                                     'warmWaterTemp': 52.9, 'roomMeasuredTemp': 20.7}, tcp_available=True, live_identity=True, health_ok=True)
            self.plugin._publish_progress(partial, set())
            self.plugin._publish(full)
            self.plugin._process_events()
        self.assertEqual(changes, [])
        for ident in (2, 3):
            self.assertTrue(self.devices[ident].pluginProps['SupportsHeatSetpoint'])
            self.assertEqual(self.devices[ident].states['status'], 'Online')
            self.assertTrue(self.devices[ident].states['dataValid'])

    def test_live_preference_controls_capabilities_and_revokes_queued_actions(self):
        self.devices[1].pluginProps['pollingEnabled'] = True
        values = readings(66, -3, 20, 46)
        values['dhwSetpoint'] = 50
        result = Result(values=values, tcp_available=True, live_identity=True, health_ok=True)
        self.plugin._publish(result)
        self.assertFalse(self.devices[2].pluginProps['SupportsHeatSetpoint'])
        self.plugin.closedPrefsConfigUi({'liveWritesEnabled': True}, False)
        self.plugin._process_events()
        self.assertTrue(self.plugin.manager.settings.live_writes)
        self.plugin._publish(result)
        self.assertTrue(self.devices[2].pluginProps['SupportsHeatSetpoint'])
        self.assertTrue(self.devices[3].pluginProps['SupportsHeatSetpoint'])
        self.devices[2].pluginProps['roomTarget'] = 'party'
        self.plugin._publish(result)
        self.assertFalse(self.devices[2].pluginProps['SupportsHeatSetpoint'])
        self.devices[2].pluginProps['roomTarget'] = 'standard'
        calls = []
        self.plugin.manager.write_setpoint = lambda *args: calls.append(args)
        self.plugin.actionControlThermostat(types.SimpleNamespace(thermostatAction=1, actionValue=22), self.devices[2])
        self.plugin.closedPrefsConfigUi({'liveWritesEnabled': False}, False)
        self.plugin._process_events()
        self.assertFalse(calls)
        self.assertFalse(self.devices[3].pluginProps['SupportsHeatSetpoint'])

    def test_pending_set_display_is_immediate_survives_poll_and_clears_after_readback(self):
        self.devices[1].pluginProps['pollingEnabled'] = True
        self.plugin._configure()
        values = readings(66, -3, 20, 46)
        values.update(roomMeasuredTemp=20.7, dhwSetpoint=50)
        result = Result(values=values, tcp_available=True, simulator=True)
        self.plugin._publish(result)
        dev = self.devices[2]
        self.plugin.actionControlThermostat(types.SimpleNamespace(thermostatAction=1, actionValue=21), dev)
        self.assertEqual(dev.states['status'], 'Pending set confirmation')
        self.assertEqual(dev.error, 'Pending set confirmation')
        self.assertEqual(dev.states['setpointHeat'], 20)
        self.plugin._publish(result)
        self.assertEqual(dev.error, 'Pending set confirmation')
        def write(*args):
            self.assertEqual(dev.error, 'Pending set confirmation')
            return 21
        self.plugin.manager.write_setpoint = write
        self.plugin._process_events()
        self.assertEqual(dev.states['setpointHeat'], 21)
        self.assertEqual(dev.states['status'], 'SIMULATOR · Standard')
        self.assertIsNone(dev.error)
        self.assertFalse(self.plugin.pending_sets)
        self.plugin.actionControlThermostat(types.SimpleNamespace(thermostatAction=1, actionValue=22), dev)
        def fail(*args): raise ValueError('readback failed')
        self.plugin.manager.write_setpoint = fail
        self.plugin._process_events()
        self.assertNotEqual(dev.states['status'], 'Pending set confirmation')
        self.assertIn('readback failed', dev.states['actionStatus'])
        self.assertEqual(dev.states['setpointHeat'], 21)
        self.assertFalse(self.plugin.pending_sets)

    def test_queued_target_change_rejects_write_and_relative_actions_use_readback(self):
        self.devices[1].pluginProps['pollingEnabled'] = True
        self.plugin._configure()
        values = readings(66, -3, 20, 46)
        values.update(roomMeasuredTemp=20.7, dhwSetpoint=50)
        self.plugin._publish(Result(values=values, tcp_available=True, simulator=True))
        calls = []
        def write(target, value, cancelled):
            calls.append((target, value))
            return value
        self.plugin.manager.write_setpoint = write
        dev = self.devices[2]
        self.plugin.actionControlThermostat(types.SimpleNamespace(thermostatAction=2, actionValue=1), dev)
        self.plugin.actionControlThermostat(types.SimpleNamespace(thermostatAction=2, actionValue=1), dev)
        self.plugin._process_events()
        self.assertEqual(calls, [('standard', 21), ('standard', 22)])
        self.plugin.actionControlThermostat(types.SimpleNamespace(thermostatAction=1, actionValue=25), dev)
        dev.pluginProps['roomTarget'] = 'reduced'
        self.plugin._process_events()
        self.assertEqual(len(calls), 2)
        self.assertIn('changed', dev.states['actionStatus'])

    def test_capability_restart_preserves_ui_and_refreshes_immediately(self):
        values = readings(66, -3, 20, 46)
        values.update(roomMeasuredTemp=20.7, dhwSetpoint=50)
        self.plugin._publish(Result(values=values, tcp_available=True, simulator=True))
        dev = self.devices[2]
        self.plugin.manager.due = 1000000000
        self.plugin.deviceStartComm(dev)
        self.assertTrue(dev.pluginProps['SupportsHeatSetpoint'])
        self.plugin._process_events()
        self.assertEqual(self.plugin.manager.due, 0)
        self.assertTrue(dev.pluginProps['SupportsHeatSetpoint'])

    def test_status_request_routes_shared_one_shot_and_retains_disabled_snapshot(self):
        self.plugin.actionControlUniversal(types.SimpleNamespace(deviceAction=1), self.devices[1])
        self.plugin.actionControlUniversal(types.SimpleNamespace(deviceAction=1), self.devices[3])
        self.plugin._process_events()
        self.assertTrue(self.plugin.manager.requested)
        self.assertFalse(self.plugin.manager.settings.enabled)
        self.assertTrue(self.devices[1].pluginProps['SupportsStatusRequest'])
        self.plugin._publish(Result(values=readings(66, -3, 20, 46), tcp_available=True))
        self.plugin._configure()
        self.assertTrue(self.devices[1].states['dataValid'])
        self.plugin.deviceStopComm(self.devices[1]); self.plugin._process_events()
        self.plugin.actionControlUniversal(types.SimpleNamespace(deviceAction=1), self.devices[3])
        self.plugin._process_events()
        self.assertFalse(self.plugin.manager.requested)

    def test_activity_detection_does_not_imply_valid_data_or_online(self):
        self.plugin._publish(Result(errors={'roomMeasuredTemp': 'timeout'}, tcp_available=True,
                                    optical_activity='Detected', optical_checked=True))
        system = self.devices[1]
        self.assertTrue(system.states['opticalActivityDetected'])
        self.assertEqual(system.states['status'], 'Pending')
        self.assertFalse(system.states['dataValid'])
        self.assertTrue(system.states['opticalActivityChecked'])
        self.plugin._publish(Result(tcp_available=True))
        self.assertFalse(system.states['opticalActivityDetected'])
        self.assertEqual(system.states['opticalActivity'], 'Unavailable')

    def test_optical_activity_status_precedence_and_no_stale_pending(self):
        for activity in ('Detected', 'Not detected', 'Unexpected byte', 'Unavailable', 'Disabled', 'Unsupported'):
            with self.subTest(activity=activity):
                self.plugin._publish(Result(errors={'roomMeasuredTemp': 'timeout'}, tcp_available=True,
                                            optical_activity=activity, optical_checked=True))
                for dev in self.devices.values():
                    expected = ('Pending' if activity == 'Detected' else
                                'System Off' if dev.id == 1 else 'Read failed')
                    self.assertEqual(dev.states['status'], expected)
                    self.assertEqual(dev.error, expected)
                    self.assertFalse(dev.states['dataValid'])
        # Valid data wins over an inconclusive optical check.
        self.plugin._publish(Result(values=readings(66, -3, 20, 46),
                                    tcp_available=True, optical_activity='Not detected'))
        for dev in self.devices.values():
            self.assertEqual(dev.states['status'], 'Online')
            self.assertIsNone(dev.error)
        # Earlier successful data and activity cannot survive a new failed cycle.
        self.plugin._publish(Result(errors={'boilerTemp': 'Connection refused'}))
        for dev in self.devices.values():
            self.assertEqual(dev.states['status'], 'Comm Fail' if dev.id == 1 else 'Connect failed')
            self.assertFalse(dev.states['dataValid'])

    def test_system_status_table_and_verified_error_precedence(self):
        cases = [
            (Result(), 'Comm Fail'),
            (Result(tcp_available=True), 'System Off'),
            (Result(tcp_available=True, optical_activity='Detected'), 'Pending'),
            (Result(values={'outsideTemp': 12}, tcp_available=True), 'Online'),
            (Result(values={'outsideTemp': 12}, tcp_available=True,
                    verified_active_fault_code='D1'), 'Error D1'),
            (Result(tcp_available=True, optical_activity='Detected',
                    verified_active_fault_code='D1'), 'Error D1'),
            # A fault retained in a disconnected/no-response result cannot
            # establish a current fault; communication evidence takes precedence.
            (Result(verified_active_fault_code='D1'), 'Comm Fail'),
            (Result(tcp_available=True, verified_active_fault_code='D1'), 'System Off'),
        ]
        for result, expected in cases:
            with self.subTest(expected=expected):
                self.plugin._publish(result)
                self.assertEqual(self.devices[1].states['status'], expected)
                self.assertEqual(self.devices[1].error, None if expected == 'Online' else expected)
        self.plugin._publish(Result(values={'outsideTemp': 12}, tcp_available=True, simulator=True,
                                    verified_active_fault_code='D1'))
        self.assertEqual(self.devices[1].states['status'], 'SIMULATOR · Error D1')
        self.assertEqual(self.devices[1].error, 'Error D1')

    def test_connection_failure_is_distinct_from_read_failure(self):
        self.plugin._publish(Result(errors={'boilerTemp': 'Connection refused'}))
        for dev in self.devices.values():
            self.assertEqual(dev.states['status'], 'Comm Fail' if dev.id == 1 else 'Connect failed')
            self.assertEqual(dev.error, 'Comm Fail' if dev.id == 1 else 'Connect failed')
        self.plugin._publish(Result(errors={'boilerTemp': 'Response timeout'}, tcp_available=True))
        for dev in self.devices.values():
            self.assertEqual(dev.states['status'], 'System Off' if dev.id == 1 else 'Read failed')
            self.assertEqual(dev.error, 'System Off' if dev.id == 1 else 'Read failed')

    def test_live_heater_uses_verified_room_temperature_with_writes_disabled(self):
        self.plugin._publish(Result(values=readings(66, -3, 20, 46), tcp_available=True))
        heater = self.devices[2]
        self.assertEqual(heater.pluginProps['NumTemperatureInputs'], 1)
        self.assertEqual(self.plugin.getDeviceDisplayStateId(heater), 'temperatureInputsAll')
        self.assertEqual(heater.states['temperatureInput1'], 20.7)
        self.assertEqual(heater.states['boilerTemp'], 66)
        self.assertTrue(heater.states['boilerTempValid'])
        self.assertFalse(heater.pluginProps['SupportsHeatSetpoint'])
        self.assertEqual(heater.states['status'], 'Online')
        self.assertIsNone(heater.error)


    def test_missing_room_read_retains_temperature_but_invalidates_heater(self):
        self.plugin._publish(Result(values=readings(66, -3, 20, 46), tcp_available=True))
        self.plugin._publish(Result(values={'roomSetpoint': 21}, errors={'roomMeasuredTemp': 'timeout'},
                                    tcp_available=True, optical_activity='Detected'))
        heater = self.devices[2]
        self.assertEqual(heater.states['temperatureInput1'], 20.7)
        self.assertFalse(heater.states['roomMeasuredTempValid'])
        self.assertFalse(heater.states['dataValid'])
        self.assertEqual(heater.states['status'], 'Pending')

    def test_unrelated_read_does_not_make_missing_child_pending(self):
        self.plugin._publish(Result(values={'warmWaterTemp': 31.1},
                                    errors={'roomSetpoint': 'Invalid reading: ERR'},
                                    tcp_available=True))
        system, heater = self.devices[1], self.devices[2]
        self.assertEqual(system.states['status'], 'Online')
        self.assertIsNone(system.error)
        self.assertFalse(system.states['dataValid'])
        self.assertIn('Invalid reading', system.states['lastError'])
        self.assertEqual(heater.states['status'], 'Read failed')
        self.assertEqual(heater.error, 'Read failed')
        self.assertFalse(heater.states['dataValid'])
        self.assertIn('Invalid reading', heater.states['lastError'])
        dhw = self.devices[3]
        self.assertEqual(dhw.states['status'], 'Online')
        self.assertTrue(dhw.states['dataValid'])
        self.assertEqual(dhw.states['warmWaterTemp'], 31.1)
        self.assertIsNone(dhw.error)
        # Retained measurements must not turn a later total failure into Pending.
        self.plugin._publish(Result(errors={'warmWaterTemp': 'Timeout'}, tcp_available=True))
        for dev in self.devices.values():
            self.assertEqual(dev.states['status'], 'System Off' if dev.id == 1 else 'Read failed')
            self.assertFalse(dev.states['dataValid'])
        self.assertEqual(dhw.states['warmWaterTemp'], 31.1)

    def test_parent_stop_and_invalid_properties_fail_closed(self):
        self.devices[1].pluginProps['pollingEnabled'] = True
        self.plugin._configure()
        self.plugin.deviceStopComm(self.devices[1]); self.plugin._process_events()
        self.plugin._configure()
        self.assertIsNone(self.plugin.manager.settings)
        self.assertEqual(self.devices[2].error, 'System unavailable')
        self.assertFalse(self.plugin.validateDeviceConfigUi(
            {'host': 'localhost', 'pollInterval': '0'}, 'viessmannSystem', 1)[0])


class BundleTests(unittest.TestCase):
    def test_indigo_dialogs_have_fields(self):
        # Indigo rejects otherwise well-formed XML dialogs with no Field elements.
        import xml.etree.ElementTree as ET
        server = ROOT / 'Viessmann.indigoPlugin/Contents/Server Plugin'
        config = ET.parse(server / 'PluginConfig.xml').getroot()
        self.assertTrue(config.findall('Field'), 'Plugin configuration dialog is empty')
        devices = ET.parse(server / 'Devices.xml').getroot()
        for device in devices.findall('Device'):
            with self.subTest(device=device.get('id')):
                self.assertTrue(device.findall('./ConfigUI/Field'), 'Device configuration dialog is empty')


if __name__ == '__main__':
    unittest.main()
