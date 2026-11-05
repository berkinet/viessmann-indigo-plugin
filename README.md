# Viessmann Indigo plugin

Read-only development build for an Indigo plugin using a Raspberry Pi running vcontrold on TCP port 3002 and Optolink to a Vitotronic 200 KO1B/KO2B.

The initial implementation provides three logical custom devices: **Viessmann system**, **Viessmann heater**, and **Viessmann water heater**. One shared manager owns a persistent TCP connection, polls the four legacy read mappings, and releases the optical link between cycles. The system's polling interval defaults to 180 seconds and is configurable. Polling is disabled by default.

No boiler write controls are implemented. The heater is currently out of service, so successful controller readings remain unverified. The owner confirmed that 0.1.0 starts in Indigo; 0.1.1 fixes its empty configuration dialog and awaits an owner UI check.

- [Setup, behavior, limitations and tests](docs/runtime.md)
- [Design context](docs/design.md)
- [Migration provenance and outstanding import gaps](docs/migration.md)
- [Development instructions](AGENTS.md)

Source bundle: `Viessmann.indigoPlugin` (development version 0.1.1).

```zsh
python3 -m unittest discover -s tests -v
```

Public repository: https://github.com/berkinet/viessmann-indigo-plugin
