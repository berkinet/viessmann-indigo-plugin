# Viessmann Indigo plugin

Development prototype for an Indigo plugin using a Raspberry Pi running vcontrold on TCP port 3002 and Optolink to a Vitotronic 200 KO1B/KO2B.

The implementation provides three logical devices: **Viessmann system**, **Viessmann heater**, and **Viessmann water heater**. One shared manager owns a persistent TCP connection, polls shared readings, and releases the optical link between cycles. The system's polling interval defaults to 180 seconds and is configurable. Polling is disabled by default.

Native thermostat children are being trialled with simulator-only, readback-verified setpoint controls. Physical boiler writes remain blocked. The heater is currently out of service, so successful controller readings remain unverified. The owner confirmed that 0.1.0 starts in Indigo; 0.1.1 fixes its empty configuration dialog and awaits an owner UI check.

- [Native thermostat trial and GitHub installation](docs/thermostat-trial.md)
- [Receive-only optical activity check](docs/optical-activity.md)
- [Read-only baseline behavior and tests](docs/runtime.md)
- [Isolated simulator for UI/configuration testing](docs/simulator.md)
- [Design context](docs/design.md)
- [OpenV support-gap comparison](docs/openv-support-gaps.md)
- [Other home automation integrations](docs/integration-survey.md)
- [Migration provenance and outstanding import gaps](docs/migration.md)
- [Development instructions](AGENTS.md)

Source bundle: `Viessmann.indigoPlugin` (development version 0.2.10).

```zsh
python3 -m unittest discover -s tests -v
```

Public repository: https://github.com/berkinet/viessmann-indigo-plugin
