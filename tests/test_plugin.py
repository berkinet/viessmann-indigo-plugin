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


class FixtureServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, answers=None, stall=False, close_reply=None):
        self.commands = []
        self.connections = 0
        self.answers = answers or ['27.4 C', '0 C', '19.0', '-2.5 C']
        self.stall = stall
        self.close_reply = close_reply
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
                        if command == 'device':
                            reply = owner.identity + '\nvctrld> '
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
    def test_persistent_socket_and_release_each_cycle(self):
        server = FixtureServer()
        client = Client(server.settings())
        try:
            for _ in range(2):
                result = client.poll()
                self.assertEqual(result.values, dict(zip(READS, (27.4, 0, 19, -2.5))))
                self.assertFalse(result.errors)
                self.assertFalse(result.release_error)
            self.assertEqual(server.connections, 1)
            self.assertEqual(server.commands, (['device'] + list(READS.values()) + ['close']) * 2)
        finally:
            client.disconnect(); server.stop()

    def test_error_text_never_becomes_reading_and_stream_stays_aligned(self):
        server = FixtureServer(['ERR: timeout after 5 seconds\nError executing getBoilerTemp',
                                'UNKNOWN', '21', '-4 C'])
        client = Client(server.settings())
        try:
            result = client.poll()
            self.assertEqual(set(result.errors), {'boilerTemp', 'outsideTemp'})
            self.assertEqual(result.values, {'roomSetpoint': 21, 'warmWaterTemp': -4})
            self.assertEqual(server.commands[-1], 'close')
        finally:
            client.disconnect(); server.stop()

    def test_timeout_disconnects_and_next_cycle_reconnects(self):
        server = FixtureServer(stall=True)
        client = Client(server.settings(timeout=1))
        try:
            start = time.monotonic()
            result = client.poll()
            self.assertLess(time.monotonic() - start, 2)
            self.assertEqual(set(result.errors), set(READS))
            self.assertIsNone(client.sock)
            self.assertEqual(server.commands, ['device'])
            server.stall = False
            self.assertEqual(len(client.poll().values), 4)
            self.assertEqual(server.connections, 2)
        finally:
            client.disconnect(); server.stop()

    def test_failed_release_disconnects_instead_of_retaining_link(self):
        server = FixtureServer(close_reply='ERR: close failed')
        client = Client(server.settings())
        try:
            result = client.poll()
            self.assertEqual(len(result.values), 4)
            self.assertTrue(result.release_error)
            self.assertIsNone(client.sock)
            server.close_reply = None
            self.assertFalse(client.poll().release_error)
            self.assertEqual(server.connections, 2)
        finally:
            client.disconnect(); server.stop()

    def test_physical_identity_blocks_writes(self):
        server = FixtureServer()
        client = Client(server.settings())
        try:
            with self.assertRaises(PermissionError):
                client.write_simulated('standard', 21)
            self.assertEqual(server.commands, ['device'])
            self.assertIsNone(client.sock)
            for target, value in [('standard', 38), ('standard', 20.5), ('dhw', 9), ('bogus', 20)]:
                with self.subTest(target=target, value=value), self.assertRaises(ValueError):
                    client.write_simulated(target, value)
            self.assertEqual(server.commands, ['device'])
        finally:
            client.disconnect(); server.stop()

    def test_strict_parse_and_read_only_allowlist(self):
        for text in ('ERR: 5', 'UNKNOWN', 'nan', '28 C\nextra', '27 boiler'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                temperature(text)
        client = Client(Settings('localhost'))
        with self.assertRaises(ValueError):
            client._exchange('setTempWWsoll 50', lambda: False)

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
                self.calls += 1; clock[0] += 20; return Result()
            def disconnect(self): self.closed = True
        manager = Manager(clock=lambda: clock[0], client_factory=Fake)
        manager.configure(Settings('localhost'))
        self.assertIsNone(manager.tick())
        self.assertEqual(instances, [])
        manager.configure(Settings('localhost', enabled=True))
        self.assertIsNotNone(manager.tick())
        clock[0] = 199
        self.assertIsNone(manager.tick())
        clock[0] = 200
        self.assertIsNotNone(manager.tick())
        self.assertEqual(len(instances), 1)
        manager.configure(Settings('localhost', interval=30, enabled=True))
        self.assertTrue(instances[0].closed)
        self.assertIsNotNone(manager.tick())
        manager.close()
        self.assertTrue(instances[-1].closed)


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
    def stateListOrDisplayStateIdChanged(self): pass
    def replacePluginPropsOnServer(self, props): self.pluginProps = dict(props)


class Devices(dict):
    def iter(self, plugin_id): return iter(self.values())


class AdapterTests(unittest.TestCase):
    def setUp(self):
        stub = types.ModuleType('indigo')
        class Base:
            def __init__(self, ident, *args): self.pluginId = ident
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
        self.plugin._publish(Result(dict(zip(READS, (25, -3, 19, 30))), tcp_available=True))
        self.assertEqual(self.devices[2].states['roomSetpoint'], 19)
        self.assertNotIn('roomTemp', self.devices[2].states)
        last = self.devices[3].states['lastSuccess']
        self.plugin._publish(Result({'boilerTemp': 26, 'outsideTemp': -4, 'roomSetpoint': 20},
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
        values = dict(zip(READS, (66, -3, 20, 46)))
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
        self.plugin._publish(Result(values=dict(zip(READS, (66, -3, 16, 46))), tcp_available=True))
        self.assertFalse(heater.pluginProps['SupportsHeatSetpoint'])
        self.assertEqual(heater.pluginProps['NumTemperatureInputs'], 0)

    def test_queued_target_change_rejects_write_and_relative_actions_use_readback(self):
        self.devices[1].pluginProps['pollingEnabled'] = True
        self.plugin._configure()
        values = dict(zip(READS, (66, -3, 20, 46)))
        values.update(roomMeasuredTemp=20.7, dhwSetpoint=50)
        self.plugin._publish(Result(values=values, tcp_available=True, simulator=True))
        calls = []
        def write(target, value, cancelled):
            calls.append((target, value))
            return value
        self.plugin.manager.write_simulated = write
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
        values = dict(zip(READS, (66, -3, 20, 46)))
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
        self.plugin._publish(Result(values=dict(zip(READS, (66, -3, 20, 46))), tcp_available=True))
        self.plugin._configure()
        self.assertTrue(self.devices[1].states['dataValid'])
        self.plugin.deviceStopComm(self.devices[1]); self.plugin._process_events()
        self.plugin.actionControlUniversal(types.SimpleNamespace(deviceAction=1), self.devices[3])
        self.plugin._process_events()
        self.assertFalse(self.plugin.manager.requested)

    def test_connection_failure_is_distinct_from_read_failure(self):
        self.plugin._publish(Result(errors={'boilerTemp': 'Connection refused'}))
        for dev in self.devices.values():
            self.assertEqual(dev.states['status'], 'Connect failed')
            self.assertEqual(dev.error, 'Connect failed')
        self.plugin._publish(Result(errors={'boilerTemp': 'Response timeout'}, tcp_available=True))
        for dev in self.devices.values():
            self.assertEqual(dev.states['status'], 'Read failed')
            self.assertEqual(dev.error, 'Read failed')

    def test_live_heater_displays_online_without_a_measured_room_input(self):
        self.plugin._publish(Result(values=dict(zip(READS, (66, -3, 20, 46))), tcp_available=True))
        heater = self.devices[2]
        self.assertEqual(heater.pluginProps['NumTemperatureInputs'], 0)
        self.assertEqual(self.plugin.getDeviceDisplayStateId(heater), 'status')
        self.assertEqual(heater.states['status'], 'Online')
        self.assertIsNone(heater.error)

    def test_incomplete_shared_snapshot_is_pending_and_preserves_details(self):
        self.plugin._publish(Result(values={'warmWaterTemp': 31.1},
                                    errors={'roomSetpoint': 'Invalid reading: ERR'},
                                    tcp_available=True))
        for device_id in (1, 2):
            dev = self.devices[device_id]
            self.assertEqual(dev.states['status'], 'Pending')
            self.assertEqual(dev.error, 'Pending')
            self.assertFalse(dev.states['dataValid'])
            self.assertIn('Invalid reading', dev.states['lastError'])
        dhw = self.devices[3]
        self.assertEqual(dhw.states['status'], 'Online')
        self.assertTrue(dhw.states['dataValid'])
        self.assertEqual(dhw.states['warmWaterTemp'], 31.1)
        self.assertIsNone(dhw.error)
        # Retained measurements must not turn a later total failure into Pending.
        self.plugin._publish(Result(errors={'warmWaterTemp': 'Timeout'}, tcp_available=True))
        for dev in self.devices.values():
            self.assertEqual(dev.states['status'], 'Read failed')
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
