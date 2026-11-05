"""Smoke-test the SYNTHETIC endpoint through the real plugin client."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'Viessmann.indigoPlugin/Contents/Server Plugin'))
from comms import Client, Settings

host = sys.argv[1] if len(sys.argv) > 1 else '192.168.5.37'
port = int(sys.argv[2]) if len(sys.argv) > 2 else 3002
client = Client(Settings(host, port=port, enabled=True))
try:
    for cycle in range(2):
        result = client.poll()
        assert result.values == {'boilerTemp': 66.0, 'outsideTemp': -3.0,
                                 'roomSetpoint': 20.0, 'warmWaterTemp': 46.0}, result
        assert not result.errors and not result.release_error, result
        print('SYNTHETIC cycle', cycle + 1, result.values)
finally:
    client.disconnect()
