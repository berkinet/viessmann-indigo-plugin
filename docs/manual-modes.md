# Manual-verified operating programs

Checked 5 November 2026 against Viessmann operating instructions 5592667 GB, March 2018, explicitly covering Vitotronic 200 KO1B, KO2B and KW6B.

Source: https://cdn0.scrvt.com/2828ebc457efab95be01dd36047e3b52/36c9022e1850de54/e2e41d426f46/Operating-Instructions-Vitotronic-200-Control.PDF

Printed page 16 defines three normal programs:

| Program | Central heating | DHW | Protection |
| --- | --- | --- | --- |
| Standby mode | Disabled | Disabled | Boiler and DHW cylinder frost protection remains active |
| Only DHW | Disabled | By temperature/time program | Frost protection enabled |
| Heating and DHW | By room temperature/time program | By temperature/time program | Not equivalent to continuous heat demand |

Use Standby rather than Off for this software program: physical shutdown is different. There is no separate heat-only program among these three. Printed page 29 describes achieving central heating without normal DHW heating by choosing Heating and DHW and setting the DHW target to 10 C. Record this as documented controller behavior, not an implemented plugin action or a recommendation to change this installation. Do not create a synthetic heat-only mode that silently changes the DHW setpoint.

The manual presents program selection by heating circuit. In the owner's single-circuit installation, one shared authoritative representation can coordinate the three logical devices; this is a plugin design choice, not evidence of a universally boiler-global protocol register. The screenshot's Only DHW label is consistent with the manual. Numeric protocol encodings, live readback and writes remain unverified.

This finding supersedes the earlier heat-only description and the unresolved semantic discrepancy. Physical configuration details remain owner-provided; the generic manual does not establish this installation's sensor/pump arrangement.

## Additional iOS app evidence — 5 November 2026

The owner supplied Screenshot 2026-11-05 at 10.29.49.png showing the Operating program selector with five choices: Standby mode; DHW only (checked); Heating and DHW; Continuous reduced; Continuous standard.

Correction: the manual's three normal programs are not an exhaustive list of the choices shown through this remote app. The app evidence establishes displayed options, not successful execution or vcontrold support. The screenshot's check mark is not proof of fresh controller readback while the heater is out of service.

The names suggest continuous reduced/standard heating operation, but their precise effects on schedules, DHW, frost protection, persistence, and protocol encoding remain unresolved. Do not invent numeric codes or infer DHW behavior. Retain these as separate candidate operating programs in the architecture until verified; do not collapse them into Heating and DHW or implement them as setpoint changes.

Use a capability-driven program list and retain unknown raw program values for diagnostics. Keep configured program separate from actual operating state and communications availability. The three logical devices and one shared communications manager are unchanged. Ownership of any circuit-specific continuous behavior remains to be confirmed.
