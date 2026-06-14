# PrusaSlicer profile

Drop your **Original Prusa MK4S** config here as `mk4s.ini` to get real print-time
and filament estimates (and a farm split balanced by actual minutes).

In PrusaSlicer: pick the MK4S 0.4mm print profile + your filament, then
**File → Export → Export Config…** and save it as `mk4s.ini` in this folder
(or set `PRUSA_CONFIG=/path/to/your.ini`).

Without this file the pipeline still works — it just balances the farm split by
part volume instead of sliced minutes.
