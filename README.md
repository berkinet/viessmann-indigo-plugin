# Viessmann Indigo plugin

Development prototype for an Indigo plugin using a Raspberry Pi running vcontrold on TCP port 3002 and Optolink to a **Viessmann Vitotronic 200, type KO2B** (confirmed from the controller nameplate supplied by the owner on 8 November 2026). Earlier KO1B/KO2B references describe the controller family; the installed controller is KO2B.

The implementation provides three logical devices: **Viessmann system**, **Viessmann heater**, and **Viessmann water heater**. One shared manager owns persistent TCP and optical connections and serializes reads and writes. Controller-clock health checks default to 30 seconds; error-history/raw-status sampling defaults to 60 seconds. Both intervals are configurable on the system device. The system's polling interval defaults to 180 seconds and is configurable. Polling is disabled by default.

Native thermostat children display measured room/DHW temperatures and provide opt-in setpoint controls. Live standard-room and DHW setpoint writes require explicit plugin-config opt-in, recent successful controller-clock health, exact KO2B identity, acknowledgement and readback; the option defaults off. Live controller time, temperatures and measured room temperature have been verified; an owner-approved provisional relay-bit interpretation drives the system fault display.

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

Source bundle: `Viessmann.indigoPlugin` (development version 0.2.15).

```zsh
python3 -m unittest discover -s tests -v
```

Public repository: https://github.com/berkinet/viessmann-indigo-plugin

Version 0.2.15 includes the owner-approved persistent-link and provisional fault-display changes. Install the release asset from GitHub. See [persistent communications](docs/persistent-communications.md).
