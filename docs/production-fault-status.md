# Production-fault status — 0.2.32

Evidence: on 16 November 2026 the production-status block became 00 00 04 00 at the 17:43:36 CET publication, while relay 82 60 still lacked its first-byte active-fault bit. The next observed fault sample published Error D1, alarm code D1 and relay 83 60 at 17:44:54. Sequential sampling cannot establish an exact physical lead time, but the plugin already had positive production-fault evidence while still displaying Online.

System status now reports Production fault whenever the last successfully decoded production-status sample has productionFault true and responding evidence is available, unless current verified fault evidence supplies a specific code. The device error flag and fault icon accompany that status. Existing burnerOff fault gating and raw telemetry are unchanged. getError0 history alone never supplies a code for a production fault.

Retain this evidence across ordinary clock/full-temperature samples and failed production reads; only a valid later production clear resets the production latch. Relay-based established codes retain their existing explicit-clear behavior. Changing controller identity by system device/host/port discards both cached fault interpretations. Communication absence retains the existing Comm Fail/System Off precedence. Diagnostics and validity flags remain independent of retained fault evidence.

Offline tests cover early production indication, clock/full-poll persistence, failed production sampling, upgrade to verified D1, successful clear, fault icon/error flag, and endpoint isolation. Earlier assertions that a production fault remained Online/idle have been updated to the new requirement. No boiler commands or local plugin installation were performed for this release.

## 0.2.33 — initial fault assessment

Owner observed Online after installing 0.2.32 while D1 remained active. Event log: restart at 18:01:56 CET, first temperatures published Online at 18:02:20, first completed fault sample published Error D1 at 18:02:48. An unmapped party read/retry extended that sample. This was an initial-assessment gap, not a valid clear sample.

After startup or an endpoint change, successful communication displays Awaiting fault check until a production-status decode or relay-based active/clear assessment succeeds. This informational startup state has no device error flag. Failed fault samples do not complete assessment; explicit fault evidence is displayed immediately. Once assessed, ordinary Online/fault/recovery behavior resumes. Child temperatures remain available independently. Tests reproduce temperatures -> failed fault sample -> production fault -> D1 -> confirmed clear.

## 0.2.34 — fault-first startup

Initial manager work now samples clock/identity and fault registers before any temperature polling. The initial fault work item omits party-mode/target reads so those cannot delay fault publication. The full temperature poll remains due immediately afterward, with the same shared connection owner. Regular sampling and write rules are unchanged. If the initial assessment fails, Awaiting fault check remains the fallback while responding; ordinary communication failure rules still apply.

The TCP fixture regression reproduces productionFault=true/relay D1, verifies no temperature commands in the first pass, then verifies the following temperature poll. This is synthetic protocol verification, not a live boiler restart test. Owner installs the release while D1 remains active for live confirmation.

## 0.2.35 — current alarm code takes priority after acknowledgment

Owner acknowledged D1 locally without resetting the burner. Relay changed from 83 60 to 82 60, but production status remained 00 00 04 00 and the current alarm block still reported D1. This disproves treating that relay-bit clear alone as complete fault clearance for display purposes.

Decode alarm byte28 only after the full 29-byte block passes existing validation. While a confirmed production fault is active, a nonzero current alarm code has priority over the generic Production fault label and the provisional relay/history-derived code. It remains cached across clock/temperature polls and missing alarm samples, with the existing validity states indicating sample availability. An explicit current code00 removes that code and leaves the generic production fault. A valid production-clear resets the cached production alarm code, so a later episode cannot inherit it. Endpoint changes also discard it. Existing provisional relay handling remains as fallback when production/current-alarm evidence is unavailable; raw evidence and burner fault gating are unchanged.

Offline TCP/adapter regression covers acknowledged D1, clock-only publication, failed alarm reads, explicit no-code fallback, successful production clear with historical D1 still present, and a later new fault without a current code.
