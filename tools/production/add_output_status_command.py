#!/usr/bin/env python3
"""Add the read-only KO2B output/status command; run on the Pi with sudo."""
from datetime import datetime, timezone
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

path = Path('/etc/vcontrold/vito.xml').resolve(strict=True)
text = path.read_text()
root = ET.fromstring(text)
existing = root.find("./commands/command[@name='getProbeOutputStatus']")
if existing is not None:
    device = existing.find("./device[@ID='209F']")
    assert device is not None and device.findtext('addr') == 'A38F' and device.findtext('len') == '2'
    assert existing.get('protocmd') == 'getaddr'
    assert existing.find('unit') is None and device.find('unit') is None
    print('Existing raw two-byte command verified')
else:
    assert text.count('</commands>') == 1
    command = '''  <command name="getProbeOutputStatus" protocmd="getaddr">
    <description>KO2B provisional output value/status, raw two-byte diagnostic; not flame proof</description>
    <device ID="209F"><addr>A38F</addr><len>2</len></device>
  </command>
'''
    updated = text.replace('</commands>', command + '</commands>')
    ET.fromstring(updated)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    backup = path.with_name(path.name + '.before-output-status-' + stamp)
    shutil.copy2(path, backup)
    path.write_text(updated)
    print('Added getProbeOutputStatus; backup: ' + str(backup))
