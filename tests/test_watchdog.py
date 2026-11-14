import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('watchdog', Path(__file__).parents[1] / 'tools/production/watchdog.py')
watchdog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(watchdog)


class WatchdogTests(unittest.TestCase):
    def test_repeated_blocked_requests_trigger_after_two_minutes(self):
        state = {}
        for now in (0, 30, 60, 90):
            self.assertFalse(watchdog.observe(state, 'Process 1 tries to aquire lock\n', now))
        self.assertTrue(watchdog.observe(state, 'Process 2 tries to aquire lock\n', 120))

    def test_powered_off_heater_with_serial_timeouts_is_not_a_lock_stall(self):
        state = {}
        for now in range(0, 600, 30):
            self.assertFalse(watchdog.observe(state, 'Process 1 tries to aquire lock\nProcess 1 got lock\n<RECV: read timeout\n', now))

    def test_healthy_owner_activity_clears_waiter_suspicion(self):
        state = {}
        watchdog.observe(state, 'Process 1 tries to aquire lock\n', 0)
        self.assertFalse(watchdog.observe(state, '<RECV: len=1 05\n', 120))
        self.assertNotIn('blocked_since', state)

    def test_idle_and_cooldown_do_not_restart(self):
        state = {}
        watchdog.observe(state, 'Process 1 tries to aquire lock\n', 0)
        self.assertFalse(watchdog.observe(state, '', 120))
        state = {'last_restart': 0}
        for now in range(30, 300, 30):
            self.assertFalse(watchdog.observe(state, 'Process 1 tries to aquire lock\n', now))

class InstalledCheckTests(unittest.TestCase):
    def test_saved_stall_restarts_once_and_persists_cooldown(self):
        import json
        import tempfile
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / 'daemon.log'
            statefile = Path(directory) / 'state.json'
            log.write_text('')
            boot = Path(directory) / 'boot'
            boot.write_text('test-boot')
            clock = [0]
            calls = []
            def run(args, **kwargs):
                from types import SimpleNamespace
                calls.append(args)
                return SimpleNamespace(returncode=0)
            with patch.object(watchdog, 'BOOT', boot), patch.object(watchdog, 'LOG', log), patch.object(watchdog, 'STATE', statefile), patch.object(watchdog.time, 'monotonic', side_effect=lambda: clock[0]), patch.object(watchdog.subprocess, 'run', side_effect=run):
                watchdog.check()  # New log baseline.
                for now in (0, 30, 60, 90, 120, 150, 180, 210, 240, 270):
                    clock[0] = now
                    with log.open('a') as stream:
                        stream.write('Process 1 tries to aquire lock\n')
                    watchdog.check()
            self.assertEqual(calls.count(['systemctl', 'restart', 'vcontrol.service']), 1)
            self.assertEqual(json.loads(statefile.read_text())['last_restart'], 120)

    def test_stopped_service_is_not_started(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        with patch.object(watchdog.subprocess, 'run', return_value=SimpleNamespace(returncode=3)) as run:
            watchdog.check()
            self.assertEqual(run.call_count, 1)


if __name__ == '__main__':
    unittest.main()
