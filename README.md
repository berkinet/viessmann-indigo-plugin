# Viessmann Indigo plugin

Development prototype for an Indigo plugin using a Raspberry Pi running vcontrold on TCP port 3002 and Optolink to a **Viessmann Vitotronic 200, type KO2B** (confirmed from the controller nameplate supplied by the owner on 8 November 2026). Earlier KO1B/KO2B references describe the controller family; the installed controller is KO2B.

The implementation provides three logical devices: **Viessmann system**, **Viessmann heater**, and **Viessmann water heater**. One shared manager owns persistent TCP and optical connections and serializes reads and writes. Controller-clock health checks default to 30 seconds; error-history/raw-status sampling defaults to 60 seconds. Both intervals are configurable on the system device. The system's polling interval defaults to 180 seconds and is configurable. Polling is disabled by default.

Native thermostat children display measured room/DHW temperatures and provide opt-in setpoint controls. Live standard-room and DHW setpoint writes require explicit plugin-config opt-in, recent successful controller-clock health, exact KO2B identity, acknowledgement and readback; the option defaults off. Live controller time, temperatures and measured room temperature have been verified; an owner-approved provisional relay-bit interpretation drives the system fault display.

- [Pi-side communications watchdog](docs/communications-watchdog.md)
- [Device icons and burner diagnostics](docs/device-icons.md)
- [Native thermostat trial and GitHub installation](docs/thermostat-trial.md)
- [Receive-only optical activity check](docs/optical-activity.md)
- [Read-only baseline behavior and tests](docs/runtime.md)
- [Isolated simulator for UI/configuration testing](docs/simulator.md)
- [Design context](docs/design.md)
- [OpenV support-gap comparison](docs/openv-support-gaps.md)
- [KO1B/KO2B integration definition comparison](docs/soprez-definition-comparison.md)
- [Measured room-temperature research](docs/room-temperature-research.md)
- [Other home automation integrations](docs/integration-survey.md)
- [Migration provenance and outstanding import gaps](docs/migration.md)
- [Development instructions](AGENTS.md)

Source bundle: `Viessmann.indigoPlugin` (development version 0.2.16).

```zsh
python3 -m unittest discover -s tests -v
```

Public repository: https://github.com/berkinet/viessmann-indigo-plugin

Version 0.2.16 includes the owner-approved persistent-link and provisional fault-display changes. Install the release asset from GitHub. See [persistent communications](docs/persistent-communications.md).

## Version 0.2.19

The system heating icon now follows valid nonzero `burnerOutput`, with healthy communications required. Invalid output uses the unknown icon; a reported system error keeps priority. System status text and the two thermostat icons are unchanged.

When valid readings show nonzero output while `burnerActive` is false, the plugin logs an error once per conflicting episode. A valid consistent pair allows a future episode to be logged; invalid readings do not clear the episode. Reads are sequential, so a single occurrence can reflect a transition between requests.

The state selectors now say **Burner active** and **Burner active reading valid**, retaining their existing state IDs. See [burner enable versus firing research](docs/burner-enable-versus-firing-2026-11-14.md) for interpretation limits.

## Version 0.2.20 — holidays and heater-local time

The system device rereads holiday departure/return dates and the active flag on every full poll (the configured polling interval, normally 180 seconds), and on a status request. `holidayStatus` reports **Unset**, **Set (not active)**, **Active**, or **Unknown**. `holidaySet`, `holidayUnset`, `holidayActive` and `holidayValid` support triggers; check validity before using retained values. External changes through the controller or app are picked up on the next poll.

Use the system device's **Set holiday departure and return dates** plugin action with YYYY-MM-DD travel dates. Requires polling, existing live-write opt-in, verified KO2B identity, the tested holiday commands in vcontrold, and a UTC vcontrold daemon. Departure must be today or later, return at least two days later, through 2099. Holiday operation starts the day after departure and ends at midnight on return. Active-program replacement and cancellation are not included. Writes are sequential, individually acknowledged/read back, and never automatically retried or rolled back; inspect the dates after a failure because a partial schedule may remain.

The new system property **Heater location time zone** defaults to `Europe/Paris`. `lastHealthCheckLocal` formats the successful response time in that zone (CET/CEST as appropriate), independent of the viewer. Existing UTC states remain unchanged. The control page can use **Last controller response (heater local time)** after this version is installed.

See [verified holiday commands and tests](docs/holiday-command-tests-2026-11-14.md). No additional physical holiday writes were performed while implementing the plugin; the previously verified 20 November / 13 December 2026 test schedule remains on the controller.

## Version 0.2.21

Dedicated Clear holiday dates action writes both 1970-01-01 reset dates and confirms Unset by readback. Normal date-setting still rejects past dates. Live clear effectiveness awaits owner testing.

## Version 0.2.22

The optional holiday control-page date variables follow confirmed heater date changes and successful Set/Clear readback. Unchanged polls preserve edits. External date changes replace edits with reported dates. Clear was live-tested successfully by the owner.
