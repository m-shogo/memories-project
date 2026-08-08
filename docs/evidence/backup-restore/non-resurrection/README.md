# Backup/Restore non-resurrection evidence

This directory is reserved for privacy-safe, production-equivalent recovery evidence referenced by `backup-restore-non-resurrection-admission-contract.v1.json`.

A generic `nonResurrectionVerification: PASS` value is not sufficient. A complete typed admission record must bind one immutable JSON evidence artifact for each required domain:

- deleted account non-resurrection
- deleted session non-resolution
- expired session terminal semantics
- revoked session terminal semantics
- Apple nonce replay rejection
- Apple authorization-code replay rejection
- deletion lease continuity
- idempotent restore effects

Evidence files must use the domain-specific filename prefixes defined by the contract, must not use mutable aliases such as `latest`, and must not contain raw URLs, credentials, tokens, account/session identifiers, IP addresses, or other sensitive recovery material.

Local PostgreSQL/MinIO restore fixtures are foundations only. They cannot be copied or relabeled into this directory as production-equivalent evidence.

Registration remains append-only and cannot establish `productionEvidence` or `productionReady`; those values remain false and application production promotion is a separate human-reviewed decision.
