# Security and privacy architecture

## Local-first defaults

- Each user has an isolated workspace and SQLite database.
- Real `data/*` workspaces are Git-ignored.
- Offline report synthesis is the default.
- The bundled investing dataset is synthetic.
- External integrations are lazy optional adapters.

## Data minimisation

Categorisation export and report evidence are explicit, user-controlled transformations. The report evidence package aggregates metrics and behaviours and excludes raw descriptions by default. Provider configuration cannot grant the LLM authority to recalculate or write transaction data.

## Secrets

API keys belong in environment variables or Streamlit secrets. `.env` and `.streamlit/secrets.toml` are ignored. Backups never store the encryption passphrase.

## Backup security

Encrypted `.nimoenc` archives use a random salt, PBKDF2-HMAC-SHA256 key derivation and authenticated Fernet encryption. Archives are hash-verified before restore, and path traversal is rejected before extraction.

## Database integrity

- SQLite foreign keys are enabled on every connection.
- Schema migrations have a ledger.
- Source files retain SHA-256 values.
- `nimo doctor` checks SQLite integrity and references.
- Superseded transactions remain auditable instead of being deleted.

## Boundaries not provided by version 1.0

NIMO is not an authenticated hosted service, key-management system, bank connector, malware scanner or regulated advice platform. Deploying it for multiple unrelated users requires additional authentication, authorisation, encrypted storage, operational logging and security review.
