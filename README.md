# Sync Up Bank to YNAB

Automatically syncs [Up Bank](https://up.com.au) transactions into [YNAB](https://www.ynab.com/) via a webhook and
an AWS Lambda function.

This is a private fork of [daveallie/up-bank-ynab-transformer](https://github.com/daveallie/up-bank-ynab-transformer),
maintained independently as a personal backup with a few behavioural changes on top of the original (see
[CHANGES.md](CHANGES.md)).

## What it does

Up Bank sends a webhook event every time a transaction is created, updated (e.g. cleared from HELD), or deleted.
This project runs as an AWS Lambda function that receives those webhook events and mirrors the change into a YNAB
budget:

- New transactions are created in YNAB, matched to the right account via a mapping you configure.
- Internal transfers between your Up accounts are created as YNAB transfers rather than duplicate transactions.
- HELD transactions are skipped until they clear, avoiding double-imports.
- Updates to an existing transaction (e.g. clearing) update the matching YNAB transaction instead of creating a
  duplicate.
- Deleted transactions are removed from YNAB.

All imported transactions are created **unapproved** in YNAB so you can review them before they affect your budget.

## Requirements

- An AWS account (this deploys a Lambda function + API Gateway endpoint via the [Serverless Framework](https://www.serverless.com/))
- An Up Bank account with API access
- A YNAB account

## Installation

### 1. Check out the code

```bash
git clone <this-repo-url>
cd sync-up-bank-to-ynab
yarn
```

### 2. Get your API keys

**Up Bank API key** — head to https://api.up.com.au/getting_started and follow the instructions. Note it down.

**YNAB API key** — head to https://app.youneedabudget.com/settings/developer and create a new Personal Access
Token. Note it down.

### 3. Set up account mappings

1. Copy `src/accountMapping.example.json` to `src/accountMapping.json` (this file is gitignored — it's personal
   configuration and should never be committed).
2. Add one entry per Up account you want to map: your transactional account, a catchall (`upId: "UP_CATCHALL"`) for
   any Up Saver you don't explicitly map, and one entry per Up Saver you do want to map individually. The `name`
   field is just for your own reference and isn't used anywhere else.
3. Get your Up account IDs:
   ```bash
   curl https://api.up.com.au/api/v1/accounts -G -H 'Authorization: Bearer <UP_API_KEY>'
   ```
   The response contains your transactional account and each of your savers — copy the relevant `id` into `upId`
   for each mapping.
4. In YNAB, create an account for the Up transaction account, each mapped Saver, and a catchall account.
5. For each mapping, open the corresponding YNAB account and copy the account ID out of the URL — it'll look like
   `https://app.youneedabudget.com/<budget-id>/accounts/<account-id>`. Set `ynabId` to that `<account-id>`.

### 4. Set up your `.env` file

1. Copy `.env.example` to `.env` (also gitignored).
2. Leave `UP_WEBHOOK_SECRET` blank for now — it's populated after the first deployment.
3. Fill in `UP_API_KEY` and `YNAB_API_KEY` with the keys from step 2.
4. Fill in `YNAB_BUDGET_ID` — visit your budget in YNAB, the URL looks like
   `https://app.youneedabudget.com/<budget-id>`. That `<budget-id>` is what you need.

### 5. Deploy

If you have AWS credentials configured under a specific named profile, add a `profile` value under `provider` in
`serverless.yml`. Otherwise you can leave it as-is and use your default AWS credentials.

#### First deployment

An extra step is needed the first time, to get the webhook URL and register it with Up.

1. Run:
   ```bash
   yarn sls deploy
   ```
2. Note down the `POST` endpoint printed under `endpoints` (e.g.
   `https://xxxxxx.execute-api.ap-southeast-2.amazonaws.com/prod/webhook/up`).
3. Register the webhook with Up, replacing `<UP_API_KEY>` and `<ENDPOINT>`:
   ```bash
   curl https://api.up.com.au/api/v1/webhooks \
     -XPOST \
     -H 'Authorization: Bearer <UP_API_KEY>' \
     -H 'Content-Type: application/json' \
     --data-binary '{
       "data": {
         "attributes": {
           "url": "<ENDPOINT>",
           "description": "Prod YNAB webhook"
         }
       }
     }'
   ```
4. Copy the `secretKey` from the response into `UP_WEBHOOK_SECRET` in `.env`.
5. Deploy again:
   ```bash
   yarn sls deploy
   ```

#### Future deployments

```bash
yarn sls deploy
```

## Personalisation that was stripped out of this repo

This repo started as a personal project, so the following files/values were removed before it was made available and
need to be recreated locally (both are gitignored, so this only needs doing once per checkout):

- `.env` — real Up/YNAB API keys, webhook secret, and YNAB budget ID. Recreate from `.env.example`.
- `src/accountMapping.json` — real Up account IDs, YNAB account IDs, and account names. Recreate from
  `src/accountMapping.example.json`.

No other personal information (names, emails, tokens) is present anywhere else in the codebase.

## Development

This is a personal backup/fork, not actively looking for outside contributions — but feel free to open an issue if
you spot a bug.
