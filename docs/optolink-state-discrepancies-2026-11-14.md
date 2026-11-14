# Reports of Optolink/state discrepancies — 14 November 2026

Read-only web research; no controller query, setting change or reset performed.

## Most relevant firsthand report: 0842 means enable, not flame

Sparxx947's Vitotronic 200 KW2 project history records on 12 October 2026 that address 0842 is the enable signal rather than flame, with 1–25 minute delays until start. This is close-family evidence for our persistent 0842=01 during burner failure. It is an owner's observation, not a manufacturer specification or proof for KO2B. The same installation initially had D1 following an empty oil tank.

The project also records an independently identified transport problem: a 266-request debug capture found 47 bus suspensions, with synchronization byte 05 incorrectly accepted as one-byte payload after resumption (21/21 affected cases). Burner state falsely switched on twice for about 15 seconds. Their mitigation accepted only 00/01 for switch values. Our sustained raw 01 and A38F C8 01 do not match that specific 05 signature, though this demonstrates why fresh serial traffic alone does not exclude framing errors.

Source: https://github.com/Sparxx947/esphome-heizung-optolink/blob/main/docs/verlauf.en.md (entries 12–14 October 2026). Findings may evolve; this is the version read on the research date.

## Fault present while official app says burner on

Owner Shypo reported on 4 March 2020 for a Vitoligno 300-C that Vitotrol Plus sent a fault code/description while ViCare asked for a heating contractor but still showed burner on. They also reported misleading healthy messages on disconnection/power loss. This establishes a similar visible symptom outside our plugin, but does not identify the internal address, distinguish cloud caching from semantics, or prove a KO2B Optolink defect.

Original post URL: https://community.viessmann.de/t5/Holz-Pellet/Vicare-und-Vitoligno-300C-Fehlercode-wird-unterschiedlich/m-p/127020 . Direct fetch failed; the original author's complete relevant post was available on their profile: https://community.viessmann.de/t5/user/viewprofilepage/user-id/12097 . Do not describe this as a measured raw-Optolink result.

## Frozen-looking data caused by wrong address/circuit

Michael Malura's firsthand Vitoladens 300-C account describes display changes not appearing in vcontrold because the configuration read inactive HK1 instead of the installed HK2. Changing to the correct circuit addresses made readings match the display. He separately reports replacing a burner-status address 55DE that never indicated on with 0842. The latter does not validate actual-flame semantics during a fault; 55DE is also not our 55E3.

Source: https://malura.de/blog/viessmann-vcontrold-hk2-bug-taktung-optimiert (16 April 2026, updated 27 June 2026).

## Conflicting burner-display interpretations

A 2018 discussion contains changing claims about demand versus B4 burner feedback. Crucially, the participant's final 18 July firsthand test on KW5 reports the burner symbol appearing with connector 41 disconnected whenever the controller issued demand, retracting an earlier contrary interpretation. Do not cite the earlier B4 speculation as settled fact. This is another controller, not proof of KO2B behavior.

Source: https://www.haustechnikdialog.de/Forum/t/209174/Viessmann-Regelung?page=2 .

## Implication for this installation

No confirmed report was found of this exact KO2B/A38F combination retaining stale burner data while Vitodata was independently shown current. The strongest lead is signal semantics: 0842 may be demand/enable, not confirmed firing. That does not yet establish A38F semantics. Preserve raw diagnostics and seek a model-specific actual operating/combustion feedback field or a synchronized on/off comparison. Do not use assumed internal cache resets or change control behavior on this evidence alone.
