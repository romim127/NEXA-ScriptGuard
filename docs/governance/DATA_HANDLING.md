# Data handling and privacy

## Local mode

In the supported default mode, the selected script is read on the user's
machine and analyzed locally. The CLI writes reports only to explicitly
selected paths. The local GUI sends the selected bytes to the loopback server
on the same machine and keeps the current report in memory. It does not
upload source or reports to a remote service.

Shareable reports are redacted by default. Redaction is heuristic and must be
reviewed before distribution. Hashes, rule IDs, locations, and other metadata
may still identify or correlate a file.

## Hosted mode

No hosted mode exists. A future remote analyzer would receive the source file
and potentially sensitive evidence over the network. Before implementation,
the project owner must approve the data flow, hosting account and region,
retention behavior, access controls, abuse limits, incident handling, and
user-facing consent. Do not send real scripts to a prototype or demo.

## Retention

The local GUI retains one report in process memory until a later analysis or
process exit. Browser downloads are saved under browser-controlled settings.
CLI outputs persist until the user removes them. NEXA does not provide
automatic retention or secure-erasure guarantees.
