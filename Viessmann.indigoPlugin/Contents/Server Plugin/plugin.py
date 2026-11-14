import queue
import threading
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
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
        self.pending_sets = {}
        self.pending_lock = threading.RLock()
        self.established_fault = ''
        self.state_images = {}
        self.burner_inconsistencies = set()

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
        self._update_state_icon(dev)
        self.events.put(('start', dev.id))

    def _update_state_icon(self, dev, updates=()):
        states = dict(dev.states)
        states.update({item['key']: item['value'] for item in updates})
        if dev.deviceTypeId == 'viessmannSystem':
            comparable = (states.get('healthValid', False) and states.get('burnerOutputValid', False)
                          and states.get('burnerStatusValid', False))
            if comparable:
                inconsistent = states.get('burnerOutput', 0) > 0 and not states.get('burnerActive', False)
                if inconsistent and dev.id not in self.burner_inconsistencies:
                    self.logger.error('%s: inconsistent burner readings: output is nonzero while burner active is off; readings are sequential, so a transition may explain a single occurrence.', dev.name)
                    self.burner_inconsistencies.add(dev.id)
                elif not inconsistent:
                    self.burner_inconsistencies.discard(dev.id)
        if dev.deviceTypeId != 'viessmannSystem':
            selector = indigo.kStateImageSel.TemperatureSensor
        elif str(states.get('status', '')).startswith(('Error ', 'SIMULATOR · Error ')):
            selector = indigo.kStateImageSel.SensorTripped
        elif not states.get('burnerOutputValid', False) or not states.get('healthValid', False):
            selector = indigo.kStateImageSel.SensorOff
        else:
            selector = (indigo.kStateImageSel.HvacHeating if states.get('burnerOutput', 0) > 0
                        else indigo.kStateImageSel.HvacOff)
        if self.state_images.get(dev.id) != selector:
            dev.updateStateImageOnServer(selector)
            self.state_images[dev.id] = selector

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

    def validateActionConfigUi(self, valuesDict, typeId, actionId):
        if typeId != 'setHoliday':
            return True, valuesDict
        errors = indigo.Dict()
        for key in ('departure', 'returning'):
            try:
                valuesDict[key] = date.fromisoformat(str(valuesDict.get(key, '')).strip()).isoformat()
            except ValueError:
                errors[key] = 'Enter a date as YYYY-MM-DD'
        return (False, valuesDict, errors) if errors else (True, valuesDict)

    def setHoliday(self, action, dev):
        try:
            if dev.deviceTypeId != 'viessmannSystem' or dev.id != self.system_id:
                raise ValueError('Select the active Viessmann system')
            departure = date.fromisoformat(str(action.props.get('departure', '')).strip()).isoformat()
            returning = date.fromisoformat(str(action.props.get('returning', '')).strip()).isoformat()
            dev.updateStatesOnServer([{'key': 'holidayActionStatus', 'value': 'Pending holiday confirmation'}])
            self.events.put(('holiday', (dev.id, departure, returning, self.manager.settings)))
        except (ValueError, TypeError) as exc:
            self.logger.error('Holiday action rejected: %s', exc)

    def clearHoliday(self, action, dev):
        if dev.deviceTypeId != 'viessmannSystem' or dev.id != self.system_id:
            self.logger.error('Select the active Viessmann system')
            return
        dev.updateStatesOnServer([{'key': 'holidayActionStatus', 'value': 'Pending holiday clear confirmation'}])
        self.events.put(('clearHoliday', (dev.id, '1970-01-01', '1970-01-01', self.manager.settings)))

    def _sync_holiday_page(self, holiday, force=False):
        # Optional control-page input variables. Refresh on actual changes only,
        # so routine polling cannot erase dates the owner is currently editing.
        pair = (holiday['holidayDeparture'], holiday['holidayReturn'])
        if not force and getattr(self, '_holiday_page_pair', None) == pair:
            return
        variables = getattr(indigo, 'variables', None)
        if variables is None:
            return
        for name, value in zip(('vitoHolidayDepartureDraft', 'vitoHolidayReturnDraft'), pair):
            if name in variables:
                indigo.variable.updateValue(variables[name].id, value=value)
        self._holiday_page_pair = pair

    def _holiday_updates(self, result):
        if result.holiday_attempted:
            updates = [{'key': 'holidayValid', 'value': result.holiday is not None},
                       {'key': 'holidayError', 'value': result.holiday_error}]
            if result.holiday is not None:
                self._sync_holiday_page(result.holiday)
                updates.extend({'key': k, 'value': v} for k, v in result.holiday.items())
                updates.append({'key': 'holidayUpdated', 'value': result.holiday_checked})
            else:
                updates.append({'key': 'holidayStatus', 'value': 'Unknown'})
            return updates
        if not result.health_ok:
            return [{'key': 'holidayValid', 'value': False}, {'key': 'holidayStatus', 'value': 'Unknown'}]
        return []

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

    def _begin_set(self, dev):
        with self.pending_lock:
            pending = self.pending_sets.setdefault(dev.id, {
                'count': 0, 'status': dev.states.get('status', 'Awaiting polling'),
                'error': None if dev.states.get('dataValid', False) else dev.states.get('status')})
            pending['count'] += 1
            dev.updateStatesOnServer([{'key': 'status', 'value': 'Pending set confirmation'},
                                      {'key': 'actionStatus', 'value': 'Pending set confirmation'}])
            # Native thermostat list displays honor the device message override.
            dev.setErrorStateOnServer('Pending set confirmation')

    def _finish_set(self, dev):
        with self.pending_lock:
            pending = self.pending_sets.get(dev.id)
            if not pending:
                return
            pending['count'] -= 1
            if pending['count']:
                return
            del self.pending_sets[dev.id]
            dev.updateStatesOnServer([{'key': 'status', 'value': pending['status']}])
            dev.setErrorStateOnServer(pending['error'])

    def _publish_states(self, dev, updates, display_error):
        with self.pending_lock:
            pending = self.pending_sets.get(dev.id)
            if pending:
                for update in updates:
                    if update['key'] == 'status':
                        pending['status'] = update['value']
                        update['value'] = 'Pending set confirmation'
                pending['error'] = display_error
                display_error = 'Pending set confirmation'
            dev.updateStatesOnServer(updates)
            dev.setErrorStateOnServer(display_error)
            self._update_state_icon(dev, updates)

    def actionControlThermostat(self, action, dev):
        kinds = {indigo.kThermostatAction.SetHeatSetpoint: 'set',
                 indigo.kThermostatAction.IncreaseHeatSetpoint: 'increase',
                 indigo.kThermostatAction.DecreaseHeatSetpoint: 'decrease'}
        kind = kinds.get(action.thermostatAction)
        if kind is None:
            self.logger.error('Unsupported thermostat action')
            return
        target = dev.pluginProps.get('roomTarget', 'standard') if dev.deviceTypeId == 'viessmannHeater' else 'dhw'
        self._begin_set(dev)
        self.events.put(('write', (dev.id, target, kind, action.actionValue, self.manager.settings)))

    def _write(self, request):
        device_id, target, kind, requested, original_settings = request
        dev = self._device(device_id)
        if dev is None or device_id not in self.active:
            if dev is not None:
                self._finish_set(dev)
            else:
                with self.pending_lock:
                    self.pending_sets.pop(device_id, None)
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
        finally:
            self._finish_set(dev)

    def getSystems(self, filter='', valuesDict=None, typeId='', targetId=0):
        return [(str(d.id), d.name) for d in indigo.devices.iter(self.pluginId)
                if d.deviceTypeId == 'viessmannSystem']

    @staticmethod
    def settings(props):
        return Settings(str(props.get('host', '')).strip(), int(props.get('port', 3002)),
                        int(props.get('pollInterval', 180)), int(props.get('timeout', 12)),
                        props.get('pollingEnabled', False) in (True, 'true', 'True'),
                        activity_probe=props.get('activityProbeEnabled', True) in (True, 'true', 'True'),
                        health_interval=int(props.get('healthInterval', 30)),
                        fault_interval=int(props.get('faultInterval', 60)),
                        heater_timezone=str(props.get('heaterTimeZone', 'Europe/Paris')).strip())

    def validateDeviceConfigUi(self, valuesDict, typeId, devId):
        errors = indigo.Dict()
        if typeId == 'viessmannSystem':
            try:
                self.settings(valuesDict)
            except (ValueError, TypeError) as exc:
                errors['showAlertText'] = str(exc) + '. Port: 1–65535; interval: 30–86400; timeout: 1–60; health/fault checks: 10–86400 seconds.'
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
                'viessmannHeater': ('roomSetpoint', 'roomMeasuredTemp'),
                'viessmannWaterHeater': ('warmWaterTemp',)}[dev.deviceTypeId]

    def _unavailable(self, dev, reason):
        if self.unavailable.get(dev.id) == reason:
            return
        self.unavailable[dev.id] = reason
        updates = [{'key': 'dataValid', 'value': False}, {'key': 'status', 'value': reason}]
        updates.extend({'key': key + 'Valid', 'value': False} for key in self._keys(dev))
        if dev.deviceTypeId == 'viessmannSystem':
            updates.extend([{'key': 'holidayValid', 'value': False},
                            {'key': 'holidayStatus', 'value': 'Unknown'},
                            {'key': 'productionStatusValid', 'value': False},
                            {'key': 'burnerOutputValid', 'value': False},
                            {'key': 'burnerStatusValid', 'value': False},
                            {'key': 'tcpAvailable', 'value': False},
                            {'key': 'opticalActivity', 'value': 'Unavailable'},
                            {'key': 'opticalActivityDetected', 'value': False},
                            {'key': 'opticalActivityError', 'value': reason}])
        self._publish_states(dev, updates, reason)

    @staticmethod
    def _system_status(result):
        if not result.tcp_available:
            return 'Comm Fail'
        responding = result.health_ok or bool(result.values) or result.optical_activity == 'Detected'
        if responding and result.verified_active_fault_code:
            return ('Error (code unavailable)' if result.verified_active_fault_code == 'Unknown'
                    else 'Error ' + result.verified_active_fault_code)
        if result.health_ok or result.values:
            return 'Online'
        if result.optical_activity == 'Detected':
            return 'Pending'
        return 'System Off'

    def _health_updates(self, result):
        updates = [{'key': 'healthValid', 'value': result.health_ok},
                   {'key': 'healthError', 'value': result.health_error}]
        if result.health_checked:
            updates.append({'key': 'lastHealthCheck', 'value': result.health_checked})
            zone = self.manager.settings.heater_timezone if self.manager.settings else 'Europe/Paris'
            local = datetime.fromisoformat(result.health_checked).astimezone(ZoneInfo(zone))
            updates.append({'key': 'lastHealthCheckLocal', 'value': local.strftime('%Y-%m-%d %H:%M:%S %Z')})
        if result.system_time:
            updates.append({'key': 'controllerTime', 'value': result.system_time})
        return updates

    @staticmethod
    def _clock_success_updates(dev, result):
        if not result.health_ok or not result.health_checked:
            return []
        previous = dev.states.get('lastSuccess', '')
        try:
            if previous and datetime.fromisoformat(previous) >= datetime.fromisoformat(result.health_checked):
                return []
        except (ValueError, TypeError):
            pass
        return [{'key': 'lastSuccess', 'value': result.health_checked}]

    def _publish_health(self, result):
        dev = self._device(self.system_id)
        if dev is None:
            return
        if result.active_fault_known or result.verified_active_fault_code:
            self.established_fault = result.verified_active_fault_code
        if result.health_ok and self.established_fault:
            result.verified_active_fault_code = self.established_fault
        status = self._system_status(result)
        if result.simulator:
            status = 'SIMULATOR · ' + status
        updates = self._health_updates(result) + self._holiday_updates(result) + self._clock_success_updates(dev, result) + [
            {'key': 'status', 'value': status},
            {'key': 'tcpAvailable', 'value': result.tcp_available}]
        if result.optical_checked:
            updates.extend([{'key': 'opticalActivity', 'value': result.optical_activity},
                            {'key': 'opticalActivityDetected', 'value': result.optical_activity == 'Detected'},
                            {'key': 'opticalActivityError', 'value': result.optical_error}])
        if not result.health_ok:
            updates.extend([{'key': 'burnerStatusValid', 'value': False},
                            {'key': 'burnerOutputValid', 'value': False},
                            {'key': 'productionStatusValid', 'value': False}])
        if result.fault_only:
            updates.extend([{'key': 'productionStatusValid', 'value': result.production_status is not None},
                            {'key': 'productionStatusError', 'value': result.production_status_error}])
            if result.production_status_raw:
                updates.append({'key': 'productionStatusRaw', 'value': result.production_status_raw})
            if result.production_status is not None:
                updates.extend({'key': key, 'value': value} for key, value in result.production_status.items())
                updates.append({'key': 'productionStatusUpdated', 'value': result.production_status_checked})
            updates.extend([{'key': 'burnerOutputValid', 'value': result.burner_output is not None},
                            {'key': 'burnerOutputError', 'value': result.burner_output_error}])
            if result.burner_output_raw:
                updates.append({'key': 'burnerOutputRaw', 'value': result.burner_output_raw})
            if result.burner_output is not None:
                updates.extend([{'key': 'burnerOutput', 'value': result.burner_output},
                                {'key': 'burnerOutputUpdated', 'value': result.burner_output_checked}])
            if result.burner_output_status is not None:
                updates.append({'key': 'burnerOutputStatus', 'value': result.burner_output_status})
            burner_valid = result.burner_status in ('00', '01')
            updates.append({'key': 'burnerStatusValid', 'value': burner_valid})
            if burner_valid:
                updates.extend([{'key': 'burnerActive', 'value': result.burner_status == '01'},
                                {'key': 'burnerStatusRaw', 'value': result.burner_status},
                                {'key': 'burnerStatusUpdated', 'value': result.burner_checked}])
            interpretation = ('Active (provisional relay bit)' if result.verified_active_fault_code
                              else 'Clear (provisional relay bit)') if result.active_fault_known else 'Unknown (last state retained)'
            updates.extend([{'key': 'faultCheckError', 'value': result.fault_error},
                            {'key': 'faultStatus', 'value': interpretation}])
            if result.fault_record:
                updates.append({'key': 'lastRecordedError', 'value': result.fault_record})
            if result.relay_status:
                updates.append({'key': 'relayStatusRaw', 'value': result.relay_status})
            if result.fault_checked:
                updates.append({'key': 'lastFaultCheck', 'value': result.fault_checked})
        self._publish_states(dev, updates, None if self._system_status(result) == 'Online' else self._system_status(result))

    def _publish_progress(self, result, published):
        if self.closing.is_set() or not self.events.empty():
            return
        ready = set()
        for ident in self.active - published:
            dev = self._device(ident)
            if dev is None or dev.deviceTypeId == 'viessmannSystem':
                continue
            if str(dev.pluginProps.get('systemId', '')) != str(self.system_id):
                continue
            required = set(self._keys(dev))
            if result.simulator:
                required.add('roomMeasuredTemp' if dev.deviceTypeId == 'viessmannHeater' else 'dhwSetpoint')
            if required <= set(result.values):
                ready.add(ident)
        if ready:
            self._publish(result, device_ids=ready, provisional=True)
            published.update(ready)

    def _publish(self, result, device_ids=None, provisional=False):
        if result.health_only:
            self._publish_health(result)
            return
        if not provisional and (result.active_fault_known or result.verified_active_fault_code):
            self.established_fault = result.verified_active_fault_code
        if self.established_fault:
            result.verified_active_fault_code = self.established_fault
        stamp = datetime.now(timezone.utc).isoformat(timespec='seconds')
        for device_id in list(self.active):
            if device_ids is not None and device_id not in device_ids:
                continue
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
                updates.extend(self._health_updates(result))
                updates.extend(self._holiday_updates(result))
                updates.extend([{'key': 'tcpAvailable', 'value': result.tcp_available},
                                {'key': 'opticalActivity', 'value': result.optical_activity},
                                {'key': 'opticalActivityDetected', 'value': result.optical_activity == 'Detected'},
                                {'key': 'opticalActivityError', 'value': result.optical_error}])
                if result.optical_checked:
                    updates.append({'key': 'opticalActivityChecked', 'value': stamp})
            reading_keys = keys + (('boilerTemp',) if dev.deviceTypeId == 'viessmannHeater' else ())
            for key in reading_keys:
                updates.append({'key': key + 'Valid', 'value': key in result.values})
                if key in result.values:
                    updates.extend([{'key': key, 'value': result.values[key]},
                                    {'key': key + 'Updated', 'value': stamp}])
            if valid:
                updates.append({'key': 'lastSuccess', 'value': stamp})
            elif dev.deviceTypeId == 'viessmannSystem':
                updates.extend(self._clock_success_updates(dev, result))
            if dev.deviceTypeId != 'viessmannSystem':
                target = dev.pluginProps.get('roomTarget', 'standard')
                target_key = 'roomSetpoint' if dev.deviceTypeId == 'viessmannHeater' else 'dhwSetpoint'
                live_allowed = (self._live_writes_enabled() and result.live_identity and result.health_ok
                                and (target == 'standard' or dev.deviceTypeId == 'viessmannWaterHeater'))
                writable = (not provisional and (result.simulator or live_allowed)
                            and valid and target_key in result.values)
                # Intermediate readings must not toggle capability properties: Indigo
                # may restart device communications when these properties change.
                if not provisional:
                    self._native_capabilities(dev, result.simulator, writable)
                if dev.deviceTypeId == 'viessmannHeater':
                    updates.append({'key': 'selectedTarget', 'value': target.title()})
                    if 'roomMeasuredTemp' in result.values:
                        updates.append({'key': 'temperatureInput1', 'value': result.values['roomMeasuredTemp']})

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
            self._publish_states(dev, updates, display_error)

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
            if action in ('holiday', 'clearHoliday'):
                ident, departure, returning, expected = device_id
                self._configure()
                dev = self._device(ident)
                if dev is None:
                    continue
                try:
                    if ident != self.system_id or expected is None or self.manager.settings != expected:
                        raise ValueError('Configuration changed before holiday action; retry explicitly')
                    actual = self.manager.write_holiday(departure, returning, self.closing.is_set, clear=action == 'clearHoliday')
                    self._sync_holiday_page(actual, force=True)
                    dev.updateStatesOnServer([{'key': k, 'value': v} for k, v in actual.items()] + [
                        {'key': 'holidayValid', 'value': True}, {'key': 'holidayError', 'value': ''},
                        {'key': 'holidayUpdated', 'value': datetime.now(timezone.utc).isoformat(timespec='seconds')},
                        {'key': 'holidayActionStatus', 'value': 'Holiday cleared; readback confirmed' if action == 'clearHoliday' else 'Holiday dates readback confirmed'}])
                except (OSError, ValueError, TypeError, KeyError) as exc:
                    dev.updateStatesOnServer([{'key': 'holidayValid', 'value': False},
                        {'key': 'holidayStatus', 'value': 'Unknown'},
                        {'key': 'holidayActionStatus', 'value': str(exc)}])
                    self.logger.error('Holiday action rejected/failed: %s', exc)
                finally:
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
                published = set()
                result = self.manager.tick(self.closing.is_set,
                                           lambda partial: self._publish_progress(partial, published))
                if result is not None and not self.closing.is_set():
                    # Discard results if Indigo stopped/reconfigured a device mid-poll.
                    if self.events.empty():
                        self._publish(result)
                self.sleep(0.5)
        except self.StopThread:
            pass
        finally:
            self.manager.close()
            with self.pending_lock:
                self.pending_sets.clear()
            for device_id in list(self.active):
                dev = self._device(device_id)
                if dev is not None:
                    self._unavailable(dev, 'Plugin stopped')

    def stopConcurrentThread(self):
        self.closing.set()
