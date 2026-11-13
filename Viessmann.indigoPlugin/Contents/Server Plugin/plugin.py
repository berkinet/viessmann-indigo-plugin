import queue
import threading
from datetime import datetime, timezone
import indigo
from comms import Manager, Settings, TARGETS


class Plugin(indigo.PluginBase):
    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        super().__init__(pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
        self.events = queue.Queue()
        self.closing = threading.Event()
        self.manager = Manager()
        self.active = set()
        self.system_id = None
        self.unavailable = {}

    def closedPrefsConfigUi(self, valuesDict, userCancelled):
        if not userCancelled:
            self.pluginPrefs.update(valuesDict)
            self.events.put(('preferences', None))

    def _live_writes_enabled(self):
        return self.pluginPrefs.get('liveWritesEnabled', False) in (True, 'true', 'True')

    def deviceStartComm(self, dev):
        # Migrate existing devices too; a new XML default alone does not update saved props.
        if dev.pluginProps.get('SupportsStatusRequest') is not True:
            props = dict(dev.pluginProps)
            props['SupportsStatusRequest'] = True
            dev.replacePluginPropsOnServer(props)
        dev.stateListOrDisplayStateIdChanged()
        self.events.put(('start', dev.id))

    def getDeviceDisplayStateId(self, dev):
        return 'status' if dev.deviceTypeId == 'viessmannSystem' else 'temperatureInputsAll'

    def deviceStopComm(self, dev):
        self.events.put(('stop', dev.id))

    def _native_capabilities(self, dev, simulator, writable):
        props = dict(dev.pluginProps)
        values = {'NumTemperatureInputs': 1,
                  'NumHumidityInputs': 0, 'SupportsHeatSetpoint': writable,
                  'SupportsCoolSetpoint': False, 'SupportsHvacOperationMode': False,
                  'SupportsHvacFanMode': False, 'ShowCoolHeatEquipmentStateUI': False}
        if any(props.get(key) != value for key, value in values.items()):
            props.update(values)
            dev.replacePluginPropsOnServer(props)
            dev.stateListOrDisplayStateIdChanged()

    def selectRoomTarget(self, action, dev):
        target = action.props.get('target', 'standard')
        if target not in ('standard', 'reduced', 'party'):
            self.logger.error('Invalid room target')
            return
        props = dict(dev.pluginProps)
        props['roomTarget'] = target
        dev.replacePluginPropsOnServer(props)
        self.events.put(('start', dev.id))

    def requestStatus(self, action, dev):
        self.events.put(('refresh', dev.id))

    def requestSystemStatus(self):
        if self.system_id is None:
            self.logger.warning('No active Viessmann system device')
            return
        self.events.put(('refresh', self.system_id))

    def actionControlUniversal(self, action, dev):
        if action.deviceAction == indigo.kUniversalAction.RequestStatus:
            self.events.put(('refresh', dev.id))

    def actionControlThermostat(self, action, dev):
        kinds = {indigo.kThermostatAction.SetHeatSetpoint: 'set',
                 indigo.kThermostatAction.IncreaseHeatSetpoint: 'increase',
                 indigo.kThermostatAction.DecreaseHeatSetpoint: 'decrease'}
        kind = kinds.get(action.thermostatAction)
        if kind is None:
            self.logger.error('Unsupported thermostat action')
            return
        target = dev.pluginProps.get('roomTarget', 'standard') if dev.deviceTypeId == 'viessmannHeater' else 'dhw'
        self.events.put(('write', (dev.id, target, kind, action.actionValue, self.manager.settings)))

    def _write(self, request):
        device_id, target, kind, requested, original_settings = request
        dev = self._device(device_id)
        if dev is None or device_id not in self.active:
            return
        try:
            if original_settings is None or original_settings != self.manager.settings:
                raise ValueError('Configuration changed before action; retry explicitly')
            current_target = dev.pluginProps.get('roomTarget', 'standard') if dev.deviceTypeId == 'viessmannHeater' else 'dhw'
            if current_target != target or str(dev.pluginProps.get('systemId', '')) != str(self.system_id):
                raise ValueError('Selected target or parent changed before action')
            simulated = dev.states.get('simulator', False)
            if not dev.states.get('dataValid', False):
                raise ValueError('A valid current reading is required before editing')
            if not simulated and (not self._live_writes_enabled() or target not in ('standard', 'dhw')):
                raise ValueError('Live setpoint writes are disabled for this target')
            value = float(requested)
            if kind != 'set':
                base = float(dev.states['setpointHeat'])
                value = base + value if kind == 'increase' else base - value
            actual = self.manager.write_setpoint(target, value, self.closing.is_set)
            # Publish only confirmed readback; the following full cycle refreshes all states.
            dev.updateStatesOnServer([{'key': 'setpointHeat', 'value': actual},
                                      {'key': 'roomSetpoint' if target != 'dhw' else 'dhwSetpoint', 'value': actual},
                                      {'key': 'actionStatus', 'value': 'Simulator readback confirmed' if simulated else 'Live readback confirmed'}])
        except (OSError, ValueError, KeyError, TypeError) as exc:
            dev.updateStatesOnServer([{'key': 'actionStatus', 'value': str(exc)}])
            self.logger.warning('Thermostat action rejected/failed: %s', exc)

    def getSystems(self, filter='', valuesDict=None, typeId='', targetId=0):
        return [(str(d.id), d.name) for d in indigo.devices.iter(self.pluginId)
                if d.deviceTypeId == 'viessmannSystem']

    @staticmethod
    def settings(props):
        return Settings(str(props.get('host', '')).strip(), int(props.get('port', 3002)),
                        int(props.get('pollInterval', 180)), int(props.get('timeout', 12)),
                        props.get('pollingEnabled', False) in (True, 'true', 'True'),
                        activity_probe=props.get('activityProbeEnabled', True) in (True, 'true', 'True'))

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
            if typeId == 'viessmannHeater' and valuesDict.get('roomTarget', 'standard') not in ('standard', 'reduced', 'party'):
                errors['roomTarget'] = 'Select standard, reduced or party.'
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
                'viessmannHeater': ('roomSetpoint', 'boilerTemp'),
                'viessmannWaterHeater': ('warmWaterTemp',)}[dev.deviceTypeId]

    def _unavailable(self, dev, reason):
        if self.unavailable.get(dev.id) == reason:
            return
        self.unavailable[dev.id] = reason
        updates = [{'key': 'dataValid', 'value': False}, {'key': 'status', 'value': reason}]
        updates.extend({'key': key + 'Valid', 'value': False} for key in self._keys(dev))
        if dev.deviceTypeId == 'viessmannSystem':
            updates.extend([{'key': 'tcpAvailable', 'value': False},
                            {'key': 'opticalActivity', 'value': 'Unavailable'},
                            {'key': 'opticalActivityDetected', 'value': False},
                            {'key': 'opticalActivityError', 'value': reason}])
        dev.updateStatesOnServer(updates)
        dev.setErrorStateOnServer(reason)

    @staticmethod
    def _system_status(result):
        if not result.tcp_available:
            return 'Comm Fail'
        responding = bool(result.values) or result.optical_activity == 'Detected'
        if responding and result.verified_active_fault_code:
            return 'Error ' + result.verified_active_fault_code
        if result.values:
            return 'Online'
        if result.optical_activity == 'Detected':
            return 'Pending'
        return 'System Off'

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
            if result.simulator and dev.deviceTypeId == 'viessmannHeater':
                valid = valid and 'roomMeasuredTemp' in result.values
            if result.simulator and dev.deviceTypeId == 'viessmannWaterHeater':
                valid = valid and 'dhwSetpoint' in result.values
            if dev.deviceTypeId == 'viessmannSystem':
                valid = valid and not result.errors and not result.release_error
            errors = [key + ': ' + message for key, message in result.errors.items()
                      if dev.deviceTypeId == 'viessmannSystem' or key in keys]
            if result.release_error:
                errors.append('Link release: ' + result.release_error)
            if not result.tcp_available:
                failure = 'Connect failed'
            elif result.optical_activity == 'Detected':
                failure = 'Pending'
            else:
                failure = 'Read failed'
            # System connectivity is independent of snapshot completeness.
            online = valid or (dev.deviceTypeId == 'viessmannSystem' and bool(result.values))
            status = self._system_status(result) if dev.deviceTypeId == 'viessmannSystem' else ('Online' if online else failure)
            display_error = None if status == 'Online' else status
            updates = [{'key': 'simulator', 'value': result.simulator}, {'key': 'lastAttempt', 'value': stamp},
                       {'key': 'dataValid', 'value': valid},
                       {'key': 'status', 'value': status},
                       {'key': 'lastError', 'value': '; '.join(errors)[:800]}]
            if dev.deviceTypeId == 'viessmannSystem':
                updates.extend([{'key': 'tcpAvailable', 'value': result.tcp_available},
                                {'key': 'opticalActivity', 'value': result.optical_activity},
                                {'key': 'opticalActivityDetected', 'value': result.optical_activity == 'Detected'},
                                {'key': 'opticalActivityError', 'value': result.optical_error}])
                if result.optical_checked:
                    updates.append({'key': 'opticalActivityChecked', 'value': stamp})
            for key in keys:
                updates.append({'key': key + 'Valid', 'value': key in result.values})
                if key in result.values:
                    updates.extend([{'key': key, 'value': result.values[key]},
                                    {'key': key + 'Updated', 'value': stamp}])
            if valid:
                updates.append({'key': 'lastSuccess', 'value': stamp})
            if dev.deviceTypeId != 'viessmannSystem':
                target = dev.pluginProps.get('roomTarget', 'standard')
                target_key = 'roomSetpoint' if dev.deviceTypeId == 'viessmannHeater' else 'dhwSetpoint'
                live_allowed = (self._live_writes_enabled() and result.live_identity
                                and not result.errors and not result.release_error
                                and (set(('boilerTemp', 'outsideTemp', 'roomSetpoint', 'warmWaterTemp', 'dhwSetpoint')) <= set(result.values))
                                and (target == 'standard' or dev.deviceTypeId == 'viessmannWaterHeater'))
                writable = (result.simulator or live_allowed) and valid and target_key in result.values
                self._native_capabilities(dev, result.simulator, writable)
                if dev.deviceTypeId == 'viessmannHeater':
                    updates.append({'key': 'selectedTarget', 'value': target.title()})
                    if result.simulator and 'roomMeasuredTemp' in result.values:
                        updates.append({'key': 'temperatureInput1', 'value': result.values['roomMeasuredTemp']})
                    elif not result.simulator and 'boilerTemp' in result.values:
                        # Provisional live display: boiler temperature, never a room target.
                        updates.append({'key': 'temperatureInput1', 'value': result.values['boilerTemp']})
                elif 'warmWaterTemp' in result.values:
                    updates.append({'key': 'temperatureInput1', 'value': result.values['warmWaterTemp']})
                if writable:
                    updates.append({'key': 'setpointHeat', 'value': result.values[target_key]})
                if target_key == 'dhwSetpoint' and target_key in result.values:
                    updates.append({'key': 'dhwSetpoint', 'value': result.values[target_key]})
            if result.simulator:
                label = 'SIMULATOR'
                if dev.deviceTypeId == 'viessmannHeater':
                    label += ' · ' + dev.pluginProps.get('roomTarget', 'standard').title()
                for update in updates:
                    if update['key'] == 'status':
                        if dev.deviceTypeId == 'viessmannSystem':
                            update['value'] = label + ' · ' + status
                        elif online:
                            update['value'] = label
            dev.updateStatesOnServer(updates)
            dev.setErrorStateOnServer(display_error)

    def _process_events(self):
        while True:
            try:
                action, device_id = self.events.get_nowait()
            except queue.Empty:
                break
            if action == 'preferences':
                self._configure()
                self.manager.request_poll()
                if not self._live_writes_enabled():
                    for ident in self.active:
                        child = self._device(ident)
                        if child and child.deviceTypeId != 'viessmannSystem' and not child.states.get('simulator', False):
                            self._native_capabilities(child, False, False)
                continue
            if action == 'refresh':
                self._configure()
                dev = self._device(device_id)
                if (dev is not None and device_id in self.active and self.manager.settings is not None
                        and (device_id == self.system_id or str(dev.pluginProps.get('systemId', '')) == str(self.system_id))):
                    self.manager.request_poll()
                continue
            if action == 'write':
                # Re-read current endpoint/target before executing queued controls.
                self._configure()
                self._write(device_id)
                continue
            dev = self._device(device_id)
            if action == 'start' and dev is not None:
                self.active.add(device_id)
                self.manager.due = 0
                self.unavailable.pop(device_id, None)
                self._unavailable(dev, 'Awaiting polling')
                if dev.deviceTypeId == 'viessmannSystem':
                    for child_id in self.active:
                        child = self._device(child_id)
                        if child is not None and str(child.pluginProps.get('systemId', '')) == str(device_id):
                            self._unavailable(child, 'Plugin restarted')
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
            from dataclasses import replace
            settings = replace(self.settings(system.pluginProps), live_writes=self._live_writes_enabled())
        except (ValueError, TypeError):
            self.manager.close()
            self.manager.settings = None
            for dev in devices:
                self._unavailable(dev, 'Invalid system configuration')
            return
        heaters = [d for d in devices if d.deviceTypeId == 'viessmannHeater' and str(d.pluginProps.get('systemId', '')) == str(system.id)]
        if len(heaters) > 1:
            self.manager.close()
            self.manager.settings = None
            for dev in devices:
                self._unavailable(dev, 'Only one heater per system is supported')
            return
        if heaters:
            from dataclasses import replace
            try:
                settings = replace(settings, target=heaters[0].pluginProps.get('roomTarget', 'standard'))
            except ValueError:
                self.manager.close()
                self.manager.settings = None
                for dev in devices:
                    self._unavailable(dev, 'Invalid selected room target')
                return
        changed = settings != self.manager.settings
        self.manager.configure(settings)
        for dev in devices:
            if dev.id != system.id and str(dev.pluginProps.get('systemId', '')) != str(system.id):
                self._unavailable(dev, 'Parent system unavailable')
            elif not settings.enabled and (changed or self.unavailable.get(dev.id) in ('Awaiting polling', 'Plugin restarted')):
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
