# Development instructions

## Project scope and evidence

Build an Indigo plugin for Vitotronic 200 KO1B/KO2B using the existing Raspberry Pi, vcontrold TCP port 3002, and Optolink. Read README.md, docs/design.md, and docs/migration.md before implementation.

Use a single shared TCP communications/polling manager. Consider three logical devices (system, central heating thermostat, domestic hot water thermostat); this device split is provisional. Do not create independent competing polling connections for logical devices.

Verify actual command names, addresses, types, units, scaling, enumeration meanings, scope, and read/write support using the deployed vito.xml and scripts. Record evidence and uncertainties. Do not infer supported commands from parameter names or another controller model. No unverified writes to the boiler. Initial discovery is read-only; unsupported controls must remain unavailable.

Preserve the 11 existing Indigo variable names where practical. Do not silently convert UNKNOWN, decoding errors, or stale data to valid readings. Do not assume the screenshot is current telemetry. Native Indigo control mappings and version compatibility require verification before implementation.

## Working preferences

Use zsh unless another shell is specifically required. Exercise independent judgment, explain evidence and tradeoffs, and preserve unresolved questions rather than inventing details.

The owner permits commits, pushes, and publication within requested work unless more specific instructions override that permission. For this project, do not create a GitHub repository until the owner explicitly confirms its name and visibility. Do not delete the source ChatGPT project or history as part of migration.

## Tests

At stage transitions (alpha, beta, release), after substantial design changes or refactoring, and periodically during sustained development, review relevant tests proportionally. Before starting a review, notify the owner of its trigger and proposed scope; this is notice, not an approval request.

Keep tests focused on requirements, meaningful failure modes, and plausible regressions. Update or remove obsolete tests, consolidate redundant coverage, and retain valuable regression protection. Avoid tests that mirror implementation. Account for maintenance and runtime costs; inspect selectively and report significant coverage changes and reasons. Do not treat test count as evidence of quality. No executable tests are needed for this initial documentation-only migration.
