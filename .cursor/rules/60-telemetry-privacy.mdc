---
description: Always apply this rule to enforce privacy and zero-PII telemetry guarantees across all backend and CLI communications.
globs: **/*.py, **/*.sh
---
# Telemetry & Privacy Invariants

As GDSS scales across Local CLI, SaaS, and Enterprise environments, absolute data sovereignty and privacy must be maintained.

## Golden Rules for Telemetry & Syncing

1. **Zero Source Code:** No file contents, commit messages, or raw developer names/emails may ever be transmitted to the SaaS or external databases.
2. **Metadata Only:** Only strictly structured metadata is permitted for telemetry (e.g., semantic drift scores, high-level symbol names if absolutely necessary for the Conflict Tensor, operation counts, CLI versions).
3. **Opt-Out is Mandatory:** All telemetry must respect a global opt-out flag (e.g., `gdss config --telemetry off` or an environment variable `GDSS_TELEMETRY=0`).
4. **Encryption:** Any network transit code must explicitly use HTTPS/TLS.

## Enforcement
- If you are writing a module that pushes data to the cloud (e.g., a SaaS sync webhook or usage reporter), ensure PII is stripped/hashed.
- Validate that the user configuration allows telemetry before invoking any network requests.
