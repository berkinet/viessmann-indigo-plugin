# Receive-only Optolink activity probe

Version 0.2.8 adds an optional system-device optical activity check, enabled by default when polling or a manual status request runs. It runs before normal register reads through the same serialized manager and TCP client. It does not run autonomously while polling is disabled.

## Operation and protocol scope

After obtaining daemon identity metadata, the plugin sends exactly this fixed daemon script for KW/KW2 configurations:

```text
raw
RECV 1
END
```

This asks vcontrold to open its configured serial adapter, flush buffered data, receive one byte, then close and release the adapter. It contains no SEND, register request or setter. Only an exact `Result: 05` counts as detection. Other bytes are reported as Unexpected byte. It detects a fresh byte during a bounded receive window, rather than observing continuous carrier or proving electrical power state.

Other protocol names are reported Unsupported, without entering raw mode. This restriction matters: vcontrold's P300 framer can transmit during device open/close, and passive idle behavior is not established for every Optolink controller. Do not expand the name allowlist without checking its actual framing configuration. The setting can be disabled in system-device configuration.

vcontrold's raw RECV can terminate its TCP child on a serial receive timeout. The plugin records Not detected with the exception, disconnects any ambiguous stream, and reconnects sequentially for ordinary polling. Its response timeout bounds the plugin wait; the daemon's serial timeout also applies. A probe can therefore add several seconds, especially when the heater is off. No detected byte does not prove the heater is off: silence, a misaligned/broken adapter, TCP failure and controller behavior can all prevent detection. Unavailable means no completed applicable check; Disabled and Unsupported are explicit.

## Indigo states (system device)

- opticalActivity: Detected, Not detected, Unexpected byte, Unavailable, Disabled, or Unsupported.
- opticalActivityDetected: true only for an exact 05 in the current result. False alone must not be interpreted as power-off; consult opticalActivity and the diagnostic.
- opticalActivityChecked: UTC publication time for the last poll that attempted the receive-only probe, not a precise per-byte timestamp. It can retain an older timestamp when a later cycle cannot attempt a probe.
- opticalActivityError: probe diagnostic, separate from normal read errors.

These fields do not make temperature data valid, do not change Online based solely on a byte, and do not establish active burner fault status. A successful register read remains separate evidence of data communication. Decoded D1 history is not a verified current-lockout field.

## Evidence and validation

Source checked against installed vcontrold commit f66b465c75f5044dd615cf773b69a93a8921fc89: src/vcontrold.c rawModus/readCmdFile, src/parser.c execCmd, src/framer.c open/close, src/semaphore.c SEM_UNDO. Raw RECV behavior and sequential recovery have fixture coverage; the probe has not been run against the owner's heater or Pi. The heater must remain off pending repair. No production service/configuration changes are needed for this plugin feature.

Sources:

- https://github.com/openv/vcontrold/blob/f66b465c75f5044dd615cf773b69a93a8921fc89/src/vcontrold.c
- https://github.com/openv/openv/wiki/Protokoll-KW
- https://github.com/openv/openv/issues/699
- https://github.com/philippoo66/optolink-splitter/discussions/170

The DIY reports demonstrate reception of periodic 05 bytes independently of register-read success on other systems. Model-specific behavior during burner lockout remains unverified on this installation.

## Brief powered-on receive-only observation — 6 November 2026

After the owner explicitly confirmed that a brief power-on was safe (remaining powered until failure was not), temporarily stopped vcontrol.service and listened directly through the existing CP2102 serial adapter at 4800 8E2. The monitor contained no serial writes or register requests. It received nine 0x05 bytes from 16:20:36.035 through 16:20:54.081 UTC, at intervals of roughly 2.2–2.4 seconds. The owner was immediately told the first byte had been detected and that the heater could be switched off. No more bytes had been observed by the subsequent checks. Power state was not independently measured.

This verifies passive reception of the expected byte on this installation, independent of any register query. It does not yet verify the plugin's raw-mode implementation end-to-end or behavior while the burner is faulted. A receive-only monitor held the serial port while vcontrold was stopped; it was not a competing serial reader. Service restoration is handled by the monitor shell's EXIT trap.


## Status heuristic — 0.2.9

The system is Online if any valid reading arrives in the current poll, independently of snapshot completeness. A child is Online when its required readings succeed. Otherwise a device reports Connect failed when TCP was not established, Pending only when the current probe detected 0x05, and Read failed when TCP connected but no qualifying data or 0x05 evidence is available. Failed/missing child reads no longer become Pending merely because an unrelated register succeeded. If the optional probe is disabled, unsupported or unavailable, it supplies no evidence for Pending.

This supersedes the 0.2.8 rule that activity was informational only. Activity alone now supports Pending, but never Online, dataValid=true or a fault-free conclusion. Per-reading validity, error details and complete-success timestamps remain separate; retained old readings/detections do not qualify a new failed poll. No controller state, polling frequency, or optical probe behavior changes in this release.
