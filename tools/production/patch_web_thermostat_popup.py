"""Guard Indigo 2026.1 web thermostat controls by advertised capabilities.

Local vendor-template workaround; an Indigo upgrade may replace it.
Run with the installed device_control_popup.html as the sole argument.
"""
from datetime import datetime, timezone
from pathlib import Path
import shutil
import sys


def patch(text):
    if '{# Viessmann: thermostat capability guards #}' in text:
        return text
    start = text.index('{% if is_thermostat %}')
    end = text.index('{% endif %}{# is_thermostat #}', start)
    section = text[start:end]
    rows = section.split("\t\t\t\t\t<div class='section-row'>")
    assert len(rows) == 5, 'Expected exactly four thermostat control rows'
    capabilities = ('supportsCoolSetpoint', 'supportsHeatSetpoint', 'supportsHvacFanMode', 'supportsHvacOperationMode')
    expected = ('decreaseCoolSetpoint', 'decreaseHeatSetpoint', 'setFanMode', 'setHvacMode')
    result = rows[0] + '{# Viessmann: thermostat capability guards #}\n'
    for row, capability, command in zip(rows[1:], capabilities, expected):
        assert 'indigo.thermostat.' + command in row
        result += '\t\t\t\t\t{% if device.' + capability + ' %}\n'
        result += "\t\t\t\t\t<div class='section-row'>" + row
        result += '\t\t\t\t\t{% endif %}\n'
    return text[:start] + result + text[end:]


if __name__ == '__main__':
    path = Path(sys.argv[1])
    original = path.read_text()
    updated = patch(original)
    if updated == original:
        print('Capability guards already installed')
    else:
        backup = path.with_name(path.name + '.before-capability-guards-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
        shutil.copy2(path, backup)
        path.write_text(updated)
        print('Updated thermostat popup; backup: ' + str(backup))
