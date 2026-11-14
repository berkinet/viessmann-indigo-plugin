#!/usr/bin/env python3
"""Install the raw four-byte KO2B production-status read; run with sudo on Pi."""
from datetime import datetime, timezone
from pathlib import Path
import re
import shutil
import xml.etree.ElementTree as ET

path = Path('/etc/vcontrold/vito.xml').resolve(strict=True)
text = path.read_text()
root = ET.fromstring(text)
command = root.find("./commands/command[@name='getProbeProductionStatus']")
assert command is not None and command.get('protocmd') == 'getaddr'
device = command.find("./device[@ID='209F']")
assert device is not None and device.findtext('addr') == 'A395'
assert device.findtext('len') in ('1', '4')
assert command.find('unit') is None and device.find('unit') is None
if device.findtext('len') == '4':
    print('Four-byte raw production-status command already configured')
else:
    matches = list(re.finditer(r'<command\b[^>]*name="getProbeProductionStatus"[^>]*>.*?</command>', text, re.S))
    assert len(matches) == 1
    match = matches[0]
    block = match.group(0)
    assert block.count('<len>1</len>') == 1
    block = block.replace('<len>1</len>', '<len>4</len>')
    block = re.sub(r'<description>.*?</description>', '<description>KO2B four-byte production status; catalog bit fields, not Siemens flame feedback</description>', block, flags=re.S)
    updated = text[:match.start()] + block + text[match.end():]
    check = ET.fromstring(updated).find("./commands/command[@name='getProbeProductionStatus']/device[@ID='209F']")
    assert check.findtext('len') == '4' and check.findtext('addr') == 'A395'
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    backup = path.with_name(path.name + '.before-production-status-4-' + stamp)
    shutil.copy2(path, backup)
    path.write_text(updated)
    print('Updated getProbeProductionStatus to four bytes; backup: ' + str(backup))
