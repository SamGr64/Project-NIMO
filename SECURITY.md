# Security and privacy

Project NIMO is designed as a local-first educational application. Financial statement files and user databases are sensitive even when the application is not connected to a bank.

## Data handling defaults

- `data/*` is excluded from Git except the synthetic `sample_user` workspace.
- Raw imported statements remain in the selected user's `raw/` directory.
- SQLite databases are stored per user under `data/<user>/database/`.
- Raw transaction descriptions are not sent to an LLM automatically.
- The bundled investing dataset is synthetic and does not require an external market-data service.
- Logs should not contain transaction values, account numbers or statement contents.

## Secrets

Keep API keys in environment variables or `.streamlit/secrets.toml`; both `.env` and Streamlit secrets are ignored by Git. Never place API keys in YAML configuration or user profiles.

## Backups

`nimo backup create` produces a verified ZIP backup. Add `--encrypt` to create a password-encrypted `.nimoenc` archive when the `security` dependency extra is installed. Passwords are not stored by NIMO. Losing the password makes the encrypted backup unrecoverable.

## Reporting and OpenAI

Offline report synthesis is the default. The OpenAI provider is opt-in and receives the structured evidence package rather than the raw transaction table. Review `config/reporting.yaml`, the generated evidence schema, and organisational policy before enabling an external provider.

## Investment scope

The investing sandbox is educational. Bundled market history is synthetic; simulations are not predictions, product recommendations or regulated financial advice.

## Reporting a vulnerability

Do not include real statements, credentials or other personal financial data in a public issue. Share a minimal synthetic reproduction privately with the repository owner.
