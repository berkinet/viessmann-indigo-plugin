# Passive Optolink capture precedents — 6 November 2026

The owner clarified that the heater need not be idle. The research target is a promiscuous/raw capture of whatever traffic occurs, including during ordinary running and conversations, with an interest in any unsolicited traffic.

## What others have done and found

- [OpenV USB-Duo/Sniffer](https://github.com/openv/openv/wiki/Bauanleitung-USB_Duo-Sniffer): hardware monitoring of heater-to-client, client-to-heater, or both directions. Its Vitoconnect example found continuing traffic even without app interaction, approximately 2.5 kB/min toward the heater and 8 kB/min back. This is evidence of an active client conversation, not proof that those data were broadcast spontaneously. Captures help investigate framing and datapoints.
- [Optolink Bridge](https://github.com/kristian/optolink-bridge): records timestamped bidirectional raw traces and provides an offline analyzer. The author's WO1C example narrows a compressor-phase candidate to 130B by examining changing state values. This is candidate discovery from a peer's requests/responses, not a demonstrated autonomous fault broadcast. Its normal transport targets VS2; our KW2 compatibility would need separate work. No Vitoconnect is established on our present optical path, so it is not a drop-in recorder for our topology.
- [FHEM hardware sniffer report, post 252](https://forum.fhem.de/index.php?topic=67744.240): an RX/TX sniffer exposed a synchronization bug after a timeout. The client sent its acknowledgement without waiting for a fresh 05, and the controller then continued emitting only 05. This is a concrete diagnostic discovery relevant to capturing failures even without finding additional registers.
- [Receive-only listen.py trace](https://github.com/philippoo66/optolink-splitter/discussions/170): a user recorded recurring 05 bytes at roughly 0.8–1.25 seconds apart. The displayed receive-only sample does not establish other spontaneous telemetry.

## What this does and does not establish

There are real precedents for passive/promiscuous capture, and they have yielded useful datapoint candidates and protocol-timing diagnoses. No convincing report of a spontaneous temperature or current-fault broadcast over our KW Optolink path was found in this search. That is not proof that none exists, nor an exhaustive observation across controller states.

Capture can run while a repaired heater operates normally. To distinguish unsolicited traffic from solicited replies, preserve both directions, time and request/response boundaries. A recorder restricted to received bytes can mistake a response requested by another participant for a broadcast. All receive data, including non-05 bytes and unparsed frames, should be preserved, not filtered to expected commands.

Recording only our existing vcontrold requests will mainly reveal those same addresses plus timing/errors. Recording a richer Vitosoft/Vitoconnect conversation could expose additional addresses, but would require an appropriate supported client and a capture topology with one coordinated serial owner or hardware tap. There is no need to make the heater idle for either experiment.

A search result about unsolicited Collect traffic in [E3onCAN](https://github.com/MyHomeMyData/E3onCAN) concerns the newer E3 CAN interface, not evidence for broadcasts over this controller's Optolink interface. Similarly openHAB's network discovery broadcasts are not heater optical broadcasts.

No hardware, Pi or heater access, code changes or installation were performed. Closer reviews of ViessData21, Optolink-Splitter and OptolinkDuoBlock remain a subsequent task; this report answers the preceding sniffer question.


The subsequent [actual-capture analysis](public-capture-analysis.md) independently checks downloadable frames and distinguishes findings reproduced there from documentation-only examples.
