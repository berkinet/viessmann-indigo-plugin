# Setpoint text entry and pending edits — 19 November 2026

The control page uses optional draft variables `vitoRoomSetpointDraft` and `vitoDhwSetpointDraft`. Tapping an entry first copies its native `setpointHeat` into the matching variable, then opens Indigo's text-entry popup. Save changes the draft only. Each separate Set button calls Indigo's native heat-setpoint setter with its own draft value; existing plugin validation, opt-in, ACK and readback safeguards remain in force. The arrow controls are retained during the trial.

Version 0.2.40 maintains `vitoRoomSetpointNote` and `vitoDhwSetpointNote`: empty after matching valid confirmation, `Press Set to apply` for an unapplied draft, and `Update pending` while that thermostat's write is outstanding. A failure releases the input lock and retains the unapplied reminder. Further setpoint inputs for the same device are ignored while pending, without queueing additional writes. The other thermostat remains usable. Invalid/failed samples cannot clear a mismatched draft.

The `control-page-assets/Viessmann Setpoint+*.png` family uses identical 120x26 dimensions: the empty/default image is white and both nonempty reminder states are yellow. It can be used as a Variable Value image bound to the matching Note, below the editable entry in z-order. Copy the image family to Indigo's Web Assets/images/controls/variables directory when rebuilding the page on another server. This uses Indigo's exact-value image selection and requires no invented controller state.

The UI trial is local to the owner's page. It does not add HVAC program controls or perform an automatic write when the popup is saved. A popup that is reopened discards its previous draft in favor of the current confirmed setpoint. Multiple clients share the draft variables; they are not independent edit sessions.

Validation covers confirmation/failure note transitions, suppression of repeated pending inputs, independent room/DHW locks, relative edits based on the last readback, and the existing lifecycle/write safeguards. An obsolete expectation that rapid taps queued two writes was updated to require a fresh input after the first readback, retaining its regression coverage.

Holiday highlighting is a follow-up requested only after this setpoint trial is verified; it is not implemented by this release.
