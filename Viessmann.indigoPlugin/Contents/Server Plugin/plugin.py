import queue
import threading
from datetime import datetime, timezone
import indigo
from comms import Manager, Settings


class Plugin(indigo.PluginBase):
    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        super().__init__(pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
        self.events = queue.Queue()
        self.closing = threading.Event()
        self.manager = Manager()
        self.active = set()
        self.system_id = None
        self.unavailable = {}

    def deviceStartComm(self, dev):
        dev.stateListOrDisplayStateIdChanged()
        self.events.put(('start', dev.id))

    def deviceStopComm(self, dev):
        self.events.put(('stop', dev.id))

    def getSystems(self, filter='', valuesDict=None, typeId='', targetId=0):
        return [(str(d.id), d.name) for d in indigo.devices.iter(self.pluginId)
                if d.deviceTypeId == 'viessmannSystem']

    @staticmethod
    def settings(props):
        return Settings(str(props.get('host', '')).strip(), int(props.get('port', 3002)),
                        int(props.get('pollInterval', 180)), int(props.get('timeout', 12)),
                        props.get('pollingEnabled', False) in (True, 'true', 'True'))

    def validateDeviceConfigUi(self, valuesDict, typeId, devId):
        errors = indigo.Dict()
        if typeId == 'viessmannSystem':
            try:
                self.settings(valuesDict)
            except (ValueError, TypeError) as exc:
                errors['showAlertText'] = str(exc) + '. Port: 1–65535; interval: 30–86400; timeout: 1–60 seconds.'
            if any(d.id != devId and d.deviceTypeId == typeId
                   for d in indigo.devices.iter(self.pluginId)):
                errors['host'] = 'Use the existing system; this version supports one boiler.'
        else:
            try:
                parent = indigo.devices[int(valuesDict.get('systemId', 0))]
                if parent.pluginId != self.pluginId or parent.deviceTypeId != 'viessmannSystem':
                    raise ValueError()
            except (KeyError, ValueError, TypeError):
                errors['systemId'] = 'Select a Viessmann system.'
        return (False, valuesDict, errors) if errors else (True, valuesDict)

    def _device(self, device_id):
        try:
            return indigo.devices[device_id]
        except KeyError:
            return None

    @staticmethod
    def _keys(dev):
        return {'viessmannSystem': ('boilerTemp', 'outsideTemp'),
                'viessmannHeater': ('roomSetpoint',),
                'viessmannWaterHeater': ('warmWaterTemp',)}[dev.deviceTypeId]

    def _unavailable(self, dev, reason):
        if self.unavailable.get(dev.id) == reason:
            return
        self.unavailable[dev.id] = reason
        updates = [{'key': 'dataValid', 'value': False}, {'key': 'status', 'value': reason}]
        updates.extend({'key': key + 'Valid', 'value': False} for key in self._keys(dev))
        if dev.deviceTypeId == 'viessmannSystem':
            updates.append({'key': 'tcpAvailable', 'value': False})
        dev.updateStatesOnServer(updates)
        dev.setErrorStateOnServer(reason)

    def _publish(self, result):
        stamp = datetime.now(timezone.utc).isoformat(timespec='seconds')
        for device_id in list(self.active):
            dev = self._device(device_id)
            if dev is None:
                continue
            if dev.deviceTypeId != 'viessmannSystem' and str(dev.pluginProps.get('systemId', '')) != str(self.system_id):
                continue
            self.unavailable.pop(dev.id, None)
            keys = self._keys(dev)
            valid = all(key in result.values for key in keys)
            if dev.deviceTypeId == 'viessmannSystem':
                valid = valid and not result.errors and not result.release_error
            errors = [key + ': ' + message for key, message in result.errors.items()
                      if dev.deviceTypeId == 'viessmannSystem' or key in keys]
            if result.release_error:
                errors.append('Link release: ' + result.release_error)
            updates = [{'key': 'lastAttempt', 'value': stamp},
                       {'key': 'dataValid', 'value': valid},
                       {'key': 'status', 'value': 'Current' if valid else 'Read failed'},
                       {'key': 'lastError', 'value': '; '.join(errors)[:800]}]
            if dev.deviceTypeId == 'viessmannSystem':
                updates.append({'key': 'tcpAvailable', 'value': result.tcp_available})
            for key in keys:
                updates.append({'key': key + 'Valid', 'value': key in result.values})
                if key in result.values:
                    updates.extend([{'key': key, 'value': result.values[key]},
                                    {'key': key + 'Updated', 'value': stamp}])
            if valid:
                updates.append({'key': 'lastSuccess', 'value': stamp})
            dev.updateStatesOnServer(updates)
            dev.setErrorStateOnServer(None if valid else 'Read failed')

    def _process_events(self):
        while True:
            try:
                action, device_id = self.events.get_nowait()
            except queue.Empty:
                break
            dev = self._device(device_id)
            if action == 'start' and dev is not None:
                self.active.add(device_id)
                self.unavailable.pop(device_id, None)
                self._unavailable(dev, 'Awaiting polling')
                if dev.deviceTypeId == 'viessmannSystem':
                    for child_id in self.active:
                        child = self._device(child_id)
                        if child is not None and str(child.pluginProps.get('systemId', '')) == str(device_id):
                            self._unavailable(child, 'System restarting')
            else:
                self.active.discard(device_id)
                if dev is not None:
                    self._unavailable(dev, 'Device stopped')
                if device_id == self.system_id:
                    self.manager.close()
                    self.manager.settings = None

    def _configure(self):
        devices = [self._device(i) for i in self.active]
        devices = [d for d in devices if d is not None]
        systems = [d for d in devices if d.deviceTypeId == 'viessmannSystem']
        if len(systems) != 1:
            self.manager.close()
            self.manager.settings = None
            self.system_id = None
            reason = 'System unavailable' if not systems else 'Multiple systems unsupported'
            for dev in devices:
                self._unavailable(dev, reason)
            return
        system = systems[0]
        self.system_id = system.id
        try:
            settings = self.settings(system.pluginProps)
        except (ValueError, TypeError):
            self.manager.close()
            self.manager.settings = None
            for dev in devices:
                self._unavailable(dev, 'Invalid system configuration')
            return
        self.manager.configure(settings)
        for dev in devices:
            if dev.id != system.id and str(dev.pluginProps.get('systemId', '')) != str(system.id):
                self._unavailable(dev, 'Parent system unavailable')
            elif not settings.enabled:
                self._unavailable(dev, 'Polling disabled')

    def runConcurrentThread(self):
        try:
            while not self.closing.is_set():
                self._process_events()
                self._configure()
                result = self.manager.tick(self.closing.is_set)
                if result is not None and not self.closing.is_set():
                    # Discard results if Indigo stopped/reconfigured a device mid-poll.
                    if self.events.empty():
                        self._publish(result)
                self.sleep(0.5)
        except self.StopThread:
            pass
        finally:
            self.manager.close()
            for device_id in list(self.active):
                dev = self._device(device_id)
                if dev is not None:
                    self._unavailable(dev, 'Plugin stopped')

    def stopConcurrentThread(self):
        self.closing.set()
