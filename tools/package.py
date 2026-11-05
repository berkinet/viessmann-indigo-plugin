"""Build a clean installer archive without caches or local configuration."""
from pathlib import Path
import plistlib
import zipfile
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parents[1]
bundle = root / 'Viessmann.indigoPlugin'
with (bundle / 'Contents/Info.plist').open('rb') as handle:
    version = plistlib.load(handle)['PluginVersion']
server = bundle / 'Contents/Server Plugin'
if not ET.parse(server / 'PluginConfig.xml').getroot().findall('Field'):
    raise ValueError('Indigo configuration dialogs require at least one Field')
out = root / 'dist' / ('Viessmann-' + version + '.indigoPlugin.zip')
out.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(bundle.rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
            archive.write(path, path.relative_to(root))
print(out)
