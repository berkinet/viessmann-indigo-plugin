# Viessmann Indigo plugin

Local design workspace for an Indigo plugin communicating with a Viessmann Vitotronic 200 KO1B/KO2B through the existing Raspberry Pi running vcontrold on TCP port 3002 and an Optolink connection.

Status: context migration and design only. No plugin implementation, verified command catalogue, or boiler write support exists yet.

## Intended architecture

One shared TCP communications and polling manager serves all logical devices. The proposed device split is a system device, central heating thermostat, and domestic hot water thermostat. The thermostat split remains provisional until supported parameters and suitable native Indigo controls are verified.

Classify each parameter by system/heating/DHW scope, read/write capability, and native Indigo control suitability. Verify commands against the installed vito.xml and current polling scripts before implementing them. Never send unverified boiler writes.

## Persistent context

- [Design and parameter inventory](docs/design.md)
- [Migration provenance and limitations](docs/migration.md)
- [Development instructions](AGENTS.md)
- [Original Indigo variables screenshot](docs/sources/indigo-variables.png)

Next step: obtain the actual deployed vito.xml and polling scripts, identify controller and runtime versions, and build an evidence-backed read-command inventory. Preserve existing Indigo variable names where practical; decide variable compatibility before replacing existing polling.

Public GitHub repository: https://github.com/berkinet/viessmann-indigo-plugin

The owner confirmed the repository name, public visibility, and publication of these documents and the variables screenshot on 5 November 2026.
