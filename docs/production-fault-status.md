# Production-fault status — 0.2.32

Evidence: on 16 November 2026 the production-status block became 00 00 04 00 at the 17:43:36 CET publication, while relay 82 60 still lacked its first-byte active-fault bit. The next observed fault sample published Error D1, alarm code D1 and relay 83 60 at 17:44:54. Sequential sampling cannot establish an exact physical lead time, but the plugin already had positive production-fault evidence while still displaying Online.

System status now reports Production fault whenever the last successfully decoded production-status sample has productionFault true and responding evidence is available, unless current verified fault evidence supplies a specific code. The device error flag and fault icon accompany that status. Existing burnerOff fault gating and raw telemetry are unchanged. getError0 history alone never supplies a code for a production fault.

Retain this evidence across ordinary clock/full-temperature samples and failed production reads; only a valid later production clear resets the production latch. Relay-based established codes retain their existing explicit-clear behavior. Changing controller identity by system device/host/port discards both cached fault interpretations. Communication absence retains the existing Comm Fail/System Off precedence. Diagnostics and validity flags remain independent of retained fault evidence.

Offline tests cover early production indication, clock/full-poll persistence, failed production sampling, upgrade to verified D1, successful clear, fault icon/error flag, and endpoint isolation. Earlier assertions that a production fault remained Online/idle have been updated to the new requirement. No boiler commands or local plugin installation were performed for this release.
