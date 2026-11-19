# Indigo web thermostat popup capability workaround — 19 November 2026

The installed Indigo 2026.1 web-server template rendered cool setpoint, heat setpoint, fan and HVAC-mode controls for every ThermostatDevice, without checking capability flags. Both Viessmann children correctly advertise SupportsHeatSetpoint=true and SupportsHvacOperationMode=false, SupportsHvacFanMode=false, SupportsCoolSetpoint=false. Mode reads defaulted to an Off presentation; attempting Heat reached our unsupported thermostat-action handler. No verified boiler-program mapping is implemented by those controls.

Applied tools/production/patch_web_thermostat_popup.py to the installed template:

`/Library/Application Support/Perceptive Automation/Indigo 2026.1/Plugins/.Web Server.indigoPlugin/Contents/Resources/templates/web_pages/v2/device_control_popup.html`

Backup beside it: `device_control_popup.html.before-capability-guards-20261119T162638Z`.

The patch wraps each control row with its corresponding device capability. It changes the local vendor template, not the Viessmann plugin or boiler commands. Other thermostats retain their supported controls. Close and reopen the popup after application; if the server retains a cached template, reloading the Web Server plugin may be required. An Indigo upgrade can replace this workaround. The guarded script is idempotent and refuses an unexpected row structure.

Validation rendered the actual patched template with Jinja StrictUndefined across all 16 capability combinations, checking that each control appeared exactly when supported. Unsupported setpoint properties were deliberately absent, verifying they were not accessed. Confirmed patch idempotence. No controller writes were performed.

The isolated server-error log at 17:20:19 contains no traceback, so its precise cause is not established. The unsupported Heat action itself returns normally from our handler and does not prove the cause of that HTTP error. User retry is needed to confirm the popup's end-to-end behavior. The backend still computes generic thermostat mode/fan context, but the template no longer exposes unsupported controls.

## Follow-up: native thermostat read requests — 0.2.39

The owner reported the same generic error just opening the heater popup, not only while changing mode. Source review found that actionControlThermostat accepted only SetHeatSetpoint, IncreaseHeatSetpoint and DecreaseHeatSetpoint; it rejected documented native thermostat read requests. Those requests now queue the existing shared refresh: RequestStatusAll, RequestMode, RequestEquipmentState, RequestTemperatures, RequestHumidities, RequestDeadbands and RequestSetpoints. Unsupported data is not invented. This is independent of the universal RequestStatus callback, which already worked.

Offline tests verify each native read request on both children queues only refresh, with no pending write or error. Unsupported mode changes remain rejected and now log the device, action, mode and value. Existing generic historical logs cannot establish which particular request caused each previous error; user verification after installation is needed. HomeKit Off/Heat controls are a separate unsupported-mode question, not made functional by accepting refresh requests.

Indigo action reference: https://docs.indigodomo.com/2025.2/scripting/reference/actions/ (ThermostatAction enumeration).
