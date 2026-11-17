"""Disable the malformed installed KO2B storage getter; never substitute an address."""
from datetime import datetime, timezone
from pathlib import Path
import re
import shutil
import xml.etree.ElementTree as ET
import sys
path = Path(sys.argv[1] if len(sys.argv) > 1 else '/etc/vcontrold/vito.xml').resolve(strict=True)
text = path.read_text()
marker = '<!-- getStorageTemp disabled: malformed KO2B address 70; replacement unverified. -->'
if marker in text:
    print('Already disabled: ' + str(path))
    sys.exit(0)
root = ET.fromstring(text)
commands = [c for c in root.findall('./commands/command') if c.get('name') == 'getStorageTemp']
assert len(commands) == 1, 'Expected exactly one storage getter'
command = commands[0]
device = command.find("./device[@ID='209F']")
assert command.get('protocmd') == 'getaddr' and device is not None
assert device.findtext('addr') == '70' and device.findtext('len') == '1'
pattern = r'<command\b(?=[^>]*\bname=[\"\x27]getStorageTemp[\"\x27])[^>]*>.*?</command>'
updated, count = re.subn(pattern, marker, text, flags=re.S)
assert count == 1
ET.fromstring(updated)
backup = path.with_name(path.name + '.before-storage-disable-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
shutil.copy2(path, backup)
path.write_text(updated)
assert not any(c.get('name') == 'getStorageTemp' for c in ET.parse(path).getroot().findall('./commands/command'))
print('Disabled getStorageTemp; backup ' + str(backup))
