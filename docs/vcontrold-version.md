# vcontrold version check — 5 November 2026

Read-only inspection; no upgrade, service restart, or boiler command performed.

- Installed /usr/local/sbin/vcontrold reports 0.98.12-5-g8ca4797 using -V.
- Pi source checkout /home/rdp/viessmann/vcontrold has origin https://github.com/openv/vcontrold.git and clean working tree, at 8ca47972c9ac5b0a14a7a36393b0dbfdb165f918 (4 September 2024).
- Installed and local build binaries have identical SHA-256: 4ba6aa417c82bcc0cc32182dc09ecf99f5115911ce90964375ecebe4f1075bfe.
- Running process executable hashing through /proc/552/exe was denied to rdp, so exact running-image equivalence is not proven.
- Live GitHub API reports latest stable release v0.98.36, published 4 November 2026 at 15:43:07 UTC. It is not marked prerelease. Release assets include ARM64 deb and zip distributions with SHA-256 sidecars.
- The release tag is 19 commits ahead of the Pi checkout. The comparison changes build/workflow files and C sources including client, parser, XML config, arithmetic, and semaphore handling. No XML definition files appear in this comparison.
- Live master HEAD: f66b465c75f5044dd615cf773b69a93a8921fc89 (4 November 2026).

Conclusion: the installed binary is not the latest upstream release. Cached web search results incorrectly still showed v0.98.12 as latest; live git refs and GitHub API were used for this conclusion.

Sources:
- https://github.com/openv/vcontrold/releases/tag/v0.98.36
- https://github.com/openv/vcontrold/compare/8ca47972c9ac5b0a14a7a36393b0dbfdb165f918...v0.98.36

Before an upgrade, inspect package contents/install behavior and relevant source changes, back up deployed binaries/configuration/startup definitions, preserve custom XML, establish rollback, then validate read-only behavior after installation. This check does not establish compatibility of the new release with this installation.

## Upgrade performed — 5 November 2026

Owner authorized the upgrade. The official ARM64 zip passed its published SHA-256 check, but its binary required GLIBC_2.38, unavailable on this Pi. Built official tag v0.98.36 (f66b465c75f5044dd615cf773b69a93a8921fc89) locally with the installed GCC 12.2 and libxml2 2.9.14; no OS/library upgrade. Build completed with a strncat warning in src/io.c:320.

Replaced only /usr/local/sbin/vcontrold; did not run make install or overwrite XML. Backups on the Pi: /home/rdp/viessmann/upgrades/v0.98.36/backup-20261105T090413Z, containing the original binary, configuration archive, configuration hashes, and preserved pre-upgrade log. Staging/source/build and baseline responses are in the parent release directory.

Initial restart failed on both versions because /tmp/vcontrold.log was owned by nobody:dialout and could not be opened during root startup. Preserved that file in the backup directory, allowing startup to create a fresh log. The new version then started successfully. Verified running PID 3487476 executable equals installed binary, version reports 0.98.36, TCP port 3002 returns vctrld>, and deployed configuration file hashes are unchanged.

All four existing read commands returned read timeouts before the upgrade. Boiler communication was therefore already failing; this upgrade must not be described as restoring live readings. Post-upgrade read verification is recorded separately below. No boiler writes were sent and the Indigo schedule was not enabled or changed.

Rollback: stop vcontrol.service, restore the backed-up vcontrold binary to /usr/local/sbin/vcontrold preserving executable permissions, and start vcontrol.service. If the same stale-log startup issue recurs, preserve the current log outside /tmp before starting; do not delete diagnostic history. No configuration rollback is currently needed because hashes were unchanged.

Post-upgrade result: all four established reads returned the same read-timeout errors as the baseline. The daemon upgrade succeeded. The owner subsequently confirmed the heater is currently out of service, which explains why live controller reads cannot presently be validated; do not classify these timeouts as an established communications defect.

Owner clarification, 5 November 2026: the heater unit is currently out of service. Defer live controller validation until it is available. Daemon version/startup/TCP checks passed; controller reads and writes remain unverified.
