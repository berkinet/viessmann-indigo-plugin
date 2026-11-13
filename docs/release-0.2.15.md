# Version 0.2.15 — approved change summary

Owner approved pushing and publishing on 13 November 2026. Installation remains owner-managed. Current production plugin remains the owner's installed version. Pi remains in production; the separate restart-capture service continues read-only logging.

1. Immediate `Pending set confirmation` display from queueing through ACK/readback or rejection. Preserve confirmed numeric targets; clear the pending message on completion/failure and retain action diagnostics.
2. Hold both TCP and optical ownership between healthy commands; no per-cycle or post-set close. Disconnect/reconnect on errors, shutdown or connection reconfiguration. This reserves the optical link against other clients until released.
3. Controller-clock health checks, default 30 seconds, configurable 10–86400 on the system device. Full readings remain separate at the existing default 180-second interval. Failed clock checks can use the existing receive-only 05 diagnostic after releasing the ambiguous held session.
4. Separate periodic error/status sampling, default 60 seconds, configurable 10–86400. Read getError0 and A152; retain raw bytes, history, timestamps and diagnostics.
5. Owner-authorized provisional KO2B fault display: first relay byte mask 01 set -> Error plus recorded code; clear -> Online when communication is good. Missing code -> Error (code unavailable). Bad/malformed/05 05 replies retain prior interpretation. Healthy time/data reads alone cannot clear a fault. Display only; no reset, write-permission or physical-control changes from the bit.
6. Heater native display uses verified measured room temperature at 0896 rather than boiler temperature; boiler remains a diagnostic state.
7. Faster live sets: reuse recent successful clock health on the same socket, check identity and individual target, then one setter, ACK and matching readback. Remove the full pre-write poll; retain opt-in, supported targets/bounds and no automatic retry.
8. Local simulator fork adds advancing clock/no-error history/relay fixtures; built and black-box tested on the Pi without replacing production. The simulator source extension is published separately in the vcontrold fork. Simulator deployment/configuration remains separate from the plugin installer.
9. System lastSuccess advances on an actual successful controller-clock read, including while a fault is displayed. Full-snapshot dataValid and child success timestamps retain their separate meanings; cached/older clock evidence cannot move lastSuccess backward.
10. Saved command inventory, probe evidence, restart-monitor source/log snapshot and transition analysis.

Validation: 41 offline tests passed; local installer ZIP packaged; XML state IDs and archive cleanliness checked. Earlier live read-only tests confirmed advancing clock checks and full data reads on held-open sessions. The final one-shot relay-decoder check encountered a getSystemTime communication error and correctly returned unknown, so that latest check did not validate a fresh live relay value. No writes/reset commands were used for these checks. Captured transitions support the decoder but its semantics remain an installation-specific trial.

Installer prepared locally at dist/Viessmann-0.2.15.indigoPlugin.zip. Owner approved GitHub publication; no local Indigo installation is performed. The temporary restart monitor was stopped and its final log archived before publication to avoid competing with persistent optical ownership.
