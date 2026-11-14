# Burner enable versus actual firing — research follow-up, 14 November 2026

No independently verified KO2B Optolink flame indicator was found in this search. No controller queries or changes were made.

## Relevant first-hand reports

- https://github.com/Sparxx947/esphome-heizung-optolink — Vitola 111 oil boiler, Vitotronic KW2 (not KO2B). Owner explicitly reports on 12 October 2026 that 0842 (our getProbeBurner1 / burnerActive) is controller enable, not flame; enable preceded actual start by 1–25 minutes. Oil preheating is only their suspected cause. Their automation uses starts, runtime and boiler-temperature changes to corroborate operation, with its alarm path not yet tested in a real event. This is useful cross-model evidence, not proof of KO2B behavior.
- https://forum.fhem.de/index.php?topic=20280.1215 — January 2017 first-hand HO1B user reports A38F byte 1 (zero-based) as burner status and byte 0 / 2 as output percent; 55D3 instead supplies modulation. Supports our getProbeOutputStatus split, but does not independently establish flame detection or lockout behavior. Our plugin already exposes the second byte as burnerOutputStatus.
- https://github.com/openv/openv/discussions/656 — KW6B owner reports mismatching stage-status addresses and unresolved behavior. Reinforces model specificity; no solution applicable to KO2B established.

## Manufacturer caveat about runtime

https://community.viessmann.de/viessmann/attachments/viessmann/customers-gas/124737/1/5727177VSA00007_1.pdf — KO1B/KO2B service manual, printed page 49, coding 1C: when B4 feedback is unavailable, runtime is compensated using an adjustable delay from the T2 start signal to fuel-valve opening (default 120 seconds subtracted at each start). Consequently, runtime increments must not automatically be treated as independent flame proof. Whether B4 feedback is present in our installation remains unverified.

## Interpretation for our installation

The corrected Indigo trigger analysis and raw serial log show getProbeBurner1 and getProbeOutputStatus tracking ordinary cycles closely this afternoon. That does not make them independent sensors, nor resolve their earlier behavior during burner lockout. A controller enable/command can follow firing during normal operation and still remain asserted during unsuccessful ignition or lockout.

Best next observational comparison: burnerActive, burnerOutput, burnerOutputStatus and known Siemens LED state during naturally occurring start/stop/fault events. No artificial fault or reset is proposed. Treat both existing fields as controller-reported operation pending direct correlation, not confirmed flame.
