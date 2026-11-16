from datetime import datetime, timezone
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET
path=Path('/etc/vcontrold/vito.xml').resolve(strict=True)
text=path.read_text(); root=ET.fromstring(text)
existing=root.find("./commands/command[@name='getProbePartyModeRaw']")
if existing is not None:
    device=existing.find("./device[@ID='209F']")
    assert existing.get('protocmd')=='getaddr' and device is not None
    assert device.findtext('addr')=='2330' and device.findtext('len')=='1'
    assert existing.find('unit') is None and device.find('unit') is None
    print('Raw party getter already verified')
else:
    assert text.count('</commands>')==1
    addition='''  <command name="getProbePartyModeRaw" protocmd="getaddr">
    <description>KO2B party mode raw byte, read-only diagnostic</description>
    <device ID="209F"><addr>2330</addr><len>1</len></device>
  </command>
'''
    updated=text.replace('</commands>', addition+'</commands>'); ET.fromstring(updated)
    backup=path.with_name(path.name+'.before-party-raw-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    shutil.copy2(path,backup);path.write_text(updated)
    print('Added read-only raw party getter; backup '+str(backup))
