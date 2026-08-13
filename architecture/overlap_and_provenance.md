# Statement overlap and provenance

## Why row deduplication is unsafe

These rows may describe two real bus journeys:

```text
2026-08-10 | TFL BUS | -1.75
2026-08-10 | TFL BUS | -1.75
```

A row-equality, merchant/date/amount or fuzzy fingerprint rule would incorrectly collapse them.

## NIMO invariant

NIMO deduplicates at the **source-file and account/date-coverage level**, not at the transaction-value level.

### Exact file protection

A SHA-256 hash prevents importing the exact same source file twice.

### Date overlap handling

For a new statement covering dates `S..E` for account `A`:

```text
UPDATE older active transactions
SET is_active = false,
    superseded_by_source_file_id = new_source
WHERE account_id = A
  AND booking_date BETWEEN S AND E;

INSERT every normalised row from the new statement;
```

This means:

- rows before `S` remain active from older statements;
- every older row in `S..E` is superseded, even if the new statement contains no transaction on one of those dates;
- identical rows in the new statement are all retained;
- other accounts are untouched;
- old rows remain queryable for audit/rollback.

## Current-day caveat

A statement downloaded during an incomplete current day may not yet contain every final transaction. The version 1.0 deterministic rule treats the imported coverage as authoritative. A later enhancement may offer an explicit “protect incomplete latest day” option; it must be opt-in and preserve the default deterministic policy.
