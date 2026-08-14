# Changes from upstream

This repo is a private, disconnected copy of
[daveallie/up-bank-ynab-transformer](https://github.com/daveallie/up-bank-ynab-transformer), kept as a personal
backup. It is not a GitHub fork (no upstream link), so this file records what's actually different from the
original at the point this repo was created.

## Behavioural changes

- **Skip HELD transactions on create** (`src/processing.ts`) — transactions with `status: "HELD"` are now skipped
  entirely on creation (previously only the negative side of internal transfers was skipped), avoiding a duplicate
  import once the transaction clears.
- **Transaction updates now patch in place instead of recreating** (`src/processing.ts`, `src/ynab/api.ts`) —
  `updateTransaction` searches YNAB by `import_id` and patches `cleared`/`approved` on the existing transaction. If
  no matching transaction is found, it falls back to creating one (`createIfNeeded`) instead of throwing. HELD
  transactions are skipped on update too.
- **All imported transactions are created unapproved** (`src/transformer.ts`, `src/ynab/api.ts`) — `approved` is
  forced to `false` on create and update, so every import needs manual review in YNAB rather than being
  auto-approved.
- **Transfer-side clearing changed** (`src/ynab/api.ts`) — the other side of an internal transfer is now always
  patched (previously only when already cleared), and is explicitly set to `Uncleared` rather than `Cleared`, and
  the update payload only sends the fields YNAB needs instead of the full transaction object.
- **Errors thrown as `Error` objects** (`src/processing.ts`) — `throw "Can't find transfer payee!"` became
  `throw new Error(...)`.
- **Blank transaction messages omitted** (`src/transformer.ts`) — `memo` is now `undefined` instead of an empty
  string when Up doesn't provide a message.

## Infrastructure changes

- **AWS region changed** to `ap-southeast-2` (was `us-east-1`) in `serverless.yml`.
- Removed the now-unnecessary `lambdaHashingVersion` setting.

## Non-behavioural

- Minor refactors (early returns instead of `if`/`else`, small helper functions) with no functional difference.
- Repo/package metadata (name, homepage, repository URL, author) updated to reflect this being an independent,
  disconnected copy rather than the upstream project.
