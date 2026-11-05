# Vitodata screenshot observations — 5 November 2026

Source: owner-provided Screenshot 2026-11-05 at 10.24.14.png. This is website evidence, not live vcontrold validation. Screenshot capture time does not establish telemetry freshness. No screenshot copy or new source payload was published.

The website groups fields into Boiler, Heating circuit A1 (Casa Milagro), and DHW, supporting the proposed three logical Indigo devices. Website visibility does not establish vcontrold availability, address, decoding, or write capability. Treat this as a candidate inventory; it is not proven to be a strict superset of Optolink capabilities.

## Boiler → Viessmann system

Outside temperature 28 C; boiler water temperature 27.4 C; Output 20 = 0: OFF; current burner type Single stage; burner stage 1 = 0: OFF; burner hours stage 1 = 5180.86 Hours; stage 2 = 0 Hours; burner starts 84269; fuel consumption = 0 Liter; subscriber number 1; Time from LON = Do not accept.

Output 20 has no verified semantic mapping. Single-stage burner information warrants checking whether burner modulation percentage is meaningful for this equipment. Zero consumption is not evidence of an implemented fuel meter.

## Heating circuit A1 → Viessmann heater

Current operating mode A1/M1 = 0: Standby mode; Operating mode A1/M1 = 1: Only DHW; external operating mode changeover = 0: OFF; standard room setpoint 19 C; reduced room setpoint 15 C; circuit pump = 0: OFF; flow temperature 56 C; measured room temperature 28.3 C; frost risk = 0: Disabled; party room setpoint 15 C; party mode = 0: OFF; economy mode = 0: OFF; holiday program Disabled; departure and return dates both 1/1/1970.

Measured room temperature is explicitly distinct from the three setpoints. Existing roomTemp reads getRoomTempSP; it cannot substitute for the displayed measurement. Current operating mode and configured Operating mode must also remain separate concepts. Holiday dates may be placeholders; do not treat them as actual scheduled holidays without verifying semantics.

## DHW → Viessmann water heater

DHW temperature (CTS1) 29.7 C; DHW heating = 0: Heating disabled; cylinder primary pump = 0: OFF; DHW circulation pump = 0: OFF.

Do not infer separate physical equipment from generic website labels. The owner's physical model remains a single boiler with an internal DHW heat exchanger. The exact CTS1 sensor location and pump mappings need verification. No DHW setpoint is visible in this screenshot, although one is declared in deployed XML.

## Mode discrepancy — resolve before implementation

The owner previously reported off, heat only, and heat and hot water. This screenshot instead explicitly shows configured mode 1 as Only DHW, with current mode 0 as Standby. These statements must not be silently reconciled. Neither screenshot values nor XML enum definitions alone establish the correct writable mode codes for the physical controller.

Until clarified, the three-device split remains valid, but the previous mode truth table is provisional and must not drive controls. Confirm whether the intended three modes are standby, DHW only, and heating plus DHW, or whether the website label is inaccurate for this installation. Confirm shared versus circuit scope and read/write encodings separately. No writes should be enabled.
