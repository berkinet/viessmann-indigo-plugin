#!/usr/bin/env python3
"""Add the read-only KO2B flame-status candidate; run on the Pi with sudo."""
from datetime import datetime, timezone
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

path = Path('/etc/vcontrold/vito.xml').resolve(strict=True)
text = path.read_text()
root = ET.fromstring(text)
existing = root.find("./commands/command[@name='getStatusFlamme']")
if existing is not None:
    device = existing.find("./device[@ID='209F']")
    assert device is not None and device.findtext('addr') == '55DD' and device.findtext('len') == '1'
    assert existing.get('protocmd') == 'getaddr'
    assert existing.find('unit') is None and device.find('unit') is None
    print('Existing raw one-byte command verified')
else:
    assert text.count('</commands>') == 1
    command = '''  <command name="getStatusFlamme" protocmd="getaddr">
    <description>UNVERIFIED KO2B flame candidate from other controller models; raw diagnostic only</description>
    <device ID="209F"><addr>55DD</addr><len>1</len></device>
  </command>
'''
    updated = text.replace('</commands>', command + '</commands>')
    ET.fromstring(updated)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    backup = path.with_name(path.name + '.before-flame-candidate-' + stamp)
    shutil.copy2(path, backup)
    path.write_text(updated)
    print('Added getStatusFlamme; backup: ' + str(backup))
