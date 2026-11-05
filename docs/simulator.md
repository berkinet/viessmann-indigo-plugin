# Isolated real-vcontrold simulator environment

Installed on 5 November 2026 at the owner's request while the heater is out of service. This exercises plugin/UI plumbing and real daemon XML/protocol decoding. Fixture values are synthetic and cannot establish that the physical controller supports any address or state.

## Installed layout

Pi directory: /home/rdp/viessmann/simulator/, containing source/, build/, config/, fixtures.json and test logs. Source originated from upstream v0.98.36 (f66b465c75f5044dd615cf773b69a93a8921fc89), copied separately from the production build checkout. CMake option VSIM=ON builds the upstream simulator with our synthetic KW2 table extension. The simulator copy also binds to loopback, resets its input buffer per session, and bounds input accumulation. These edits are not changes to the production daemon. Source lineage: https://github.com/openv/vcontrold/blob/v0.98.36/src/vsim.c (GPL-3.0-or-later).

The upstream simulator's fixed table does not cover our current reads, so fixtures were explicitly added. They include boiler 66 C, outside -3 C, standard room target 20 C, DHW 46 C, reduced target 16 C, party target 22 C, and candidate probe raw values. Program byte 02 is an arbitrary fixture, not a verified KO2B encoding. Values do not evolve or model heating physics. Writes are not simulated.

Two installed systemd units run as unprivileged rdp and are enabled at boot:

- vcontrold-simulator.service: vsim on 127.0.0.1:6578.
- vcontrold-test.service: real installed vcontrold 0.98.36, separate read-only XML, 127.0.0.1:3003, device override 127.0.0.1:6578. Has its own log and PID paths.

Both have PrivateDevices and loopback-only IP restrictions. The test daemon does not open the physical serial adapter. Its command XML snapshot excludes every non-getaddr definition, including all setters. It is independent of subsequent production XML changes. The production port 3002, active XML, binary and service were not modified or restarted; hashes and original PID 3487476 were verified unchanged.

Initial XML serialization removed an unused namespace declaration required by vcontrold. The TEST configuration was corrected to retain xmlns:vcontrol explicitly; test service startup then succeeded. The committed preparation script includes that correction. Building only vsim from the separate source copy reported an unknown generated version header because git metadata was omitted; the TCP-facing daemon uses the installed versioned production binary, not that generated header.

## Original tunnel setup (superseded below)

A local SSH tunnel was started on this Mac:

```zsh
ssh -M -S /private/tmp/viessmann-vsim/ssh-control -fNT \
  -o BatchMode=yes -o ExitOnForwardFailure=yes \
  -o ServerAliveInterval=30 -o ServerAliveCountMax=3 \
  -L 127.0.0.1:13003:127.0.0.1:3003 rdp@192.168.5.37
```

The tunnel is not installed as a boot service. It needs restarting if SSH drops or this Mac restarts. Ensure the temporary directory exists first. Do not start another tunnel while the existing one owns port 13003.

To check or close the current tunnel:

```zsh
ssh -S /private/tmp/viessmann-vsim/ssh-control -O check rdp@192.168.5.37
ssh -S /private/tmp/viessmann-vsim/ssh-control -O exit rdp@192.168.5.37
```

For Indigo testing, edit the existing system device to host 127.0.0.1, port 13003 and enable polling. Clearly label its name/description SIMULATOR so synthetic readings are not confused with the real heater. Its children continue to reference that parent; the initial plugin supports only one system device. These device edits have NOT been applied by the agent. Disable polling before changing endpoints. To return to real hardware after repair, select host 192.168.5.37, port 3002 and deliberately enable polling when ready. Do not select the backend vsim port 6578: it speaks optical protocol bytes, not the text client protocol.

The installed plugin remains 0.1.1 with custom read-only devices; installing vsim does not itself implement native thermostat controls, target selection or setters.

## Verification and reproduction

```zsh
python3 tools/simulator/check.py
```

Two consecutive cycles through the actual plugin Client returned all four expected values with no parse/release errors, validating persistent TCP and close/reacquire against real vcontrold. All nine read probes were separately exercised ONLY on the test daemon and produced fixture responses. Its command catalogue contained no setters. The normal production daemon remained active.

The preparation script and fixture manifest are under tools/simulator/. prepare_on_pi.py is a Pi-side setup helper for the documented source location and requires a new, absent simulator directory; it does not install the systemd units by itself. The live unit files are in /etc/systemd/system and their definitions are preserved alongside that helper. No upstream source is vendored into the plugin bundle.

To stop the test environment, use sudo systemctl stop vcontrold-test vcontrold-simulator on the Pi. To prevent startup at boot, also disable those two units. Never substitute the production vcontrol.service name in these commands.

## Current endpoint: direct Pi port 3002

At the owner's explicit request, the unused physical-heater vcontrold was stopped and its vcontrol.service disabled. The old no-argument daemon PID 3487476 remained alive after the initial SysV disable operation and was explicitly terminated after verifying its executable and arguments. vcontrol.service is now inactive and disabled.

The simulator-backed vcontrold-test.service now listens on **192.168.5.37:3002**, permitted to localhost and 192.168.5.0/24. Its backend remains **127.0.0.1:6578** (vsim), with physical-device access disabled. Both simulator services remain enabled at boot. Port 3003 is no longer used. A vcontrold process is intentionally still running: it is the text-protocol frontend to vsim, not a connection to the heater. Verified PID 3915402 has explicit simulator configuration and device arguments; vsim PID 3899974 owns loopback port 6578.

Two direct polls from the Indigo Mac to 192.168.5.37:3002 returned the expected four synthetic values with no release errors. The owner switched the Indigo system device to the direct endpoint. The obsolete Mac SSH tunnel was stopped. The smoke-test helper now defaults to the direct Pi endpoint. No plugin binary update is required.

Production main/command XML symlinks remain unchanged. Copies of the test unit/config before the port switch are retained beside those files with before-port-switch suffixes. To restore real hardware after repair: stop/disable vcontrold-test.service first to release 3002, then enable/start vcontrol.service. Stop/disable vsim too if no longer needed. Keep a SIMULATOR label on the Indigo device until that deliberate switch and real-read validation; the shared endpoint cannot itself distinguish simulated versus physical readings.
