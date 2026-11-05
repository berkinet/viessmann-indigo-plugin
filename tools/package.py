"""Build a clean installer archive without caches or local configuration."""
from pathlib import Path
import plistlib
import zipfile

root = Path(__file__).resolve().parents[1]
bundle = root / 'Viessmann.indigoPlugin'
with (bundle / 'Contents/Info.plist').open('rb') as handle:
    version = plistlib.load(handle)['PluginVersion']
out = root / 'dist' / ('Viessmann-' + version + '.indigoPlugin.zip')
out.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(bundle.rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
            archive.write(path, path.relative_to(root))
print(out)
