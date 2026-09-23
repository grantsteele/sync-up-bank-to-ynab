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
- **Lambda runtime upgraded to `nodejs24.x`** (was `nodejs16.x`), since AWS blocks creating Node 16 functions from
  1 Feb 2027 and updating them from 3 Mar 2027. Serverless v3's config schema predates Node 24, so deploys print a
  harmless `provider.runtime` validation warning.
- **Build switched from `serverless-plugin-typescript` to `serverless-esbuild`**, which bundles the code and its
  libraries into a single file. With newer npm versions, Serverless v3's dev-dependency exclusion runs
  `npm ls --prod`, which npm now rejects; Serverless then treats every package as a dev dependency and ships a
  function with no `node_modules`, which crashes on load (`Cannot find module 'up-bank-api'`, surfacing as a 502 to
  Up). Bundling sidesteps that check entirely. esbuild doesn't type-check, so run `npx tsc --noEmit` if you want
  type errors reported.

## Non-behavioural

- Minor refactors (early returns instead of `if`/`else`, small helper functions) with no functional difference.
- Repo/package metadata (name, homepage, repository URL, author) updated to reflect this being an independent,
  disconnected copy rather than the upstream project.
