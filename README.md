# Sync Up Bank to YNAB

Automatically syncs [Up Bank](https://up.com.au) transactions into [YNAB](https://www.ynab.com/) — no manual
importing, ever again.

This is a private fork of [daveallie/up-bank-ynab-transformer](https://github.com/daveallie/up-bank-ynab-transformer),
maintained independently as a personal backup with a few behavioural changes on top of the original (see
[CHANGES.md](CHANGES.md)).

## What it does, in plain English

Every time a transaction happens on your Up account, Up sends a little notification to a web address ("a webhook").
This project gives it an address to send that notification to, and turns it into a matching transaction in your
YNAB budget automatically.

- New transactions show up in YNAB, in the right account.
- Transfers between your own Up accounts (e.g. moving money into a Saver) show up as a single YNAB transfer, not
  two separate transactions.
- Transactions that are still "pending" (Up calls this HELD) are ignored until they finish clearing, so you don't
  get it twice.
- If a transaction changes (e.g. it clears) or gets deleted on Up's side, the matching YNAB transaction is updated
  or deleted too.

Everything comes into YNAB **unapproved**, so nothing affects your budget until you've glanced at it and approved
it yourself.

---

## Step-by-step setup guide

This guide assumes no prior AWS experience. It's broken into small steps — work through them in order and you'll
have this running in well under an hour.

### What you'll need before you start

| Thing | What it's for | Cost |
|---|---|---|
| A computer with [Node.js](https://nodejs.org/) and [Yarn](https://yarnpkg.com/) installed | To run the setup commands | Free |
| An [Up Bank](https://up.com.au) account | The bank you're syncing from | Free |
| A [YNAB](https://www.ynab.com/) account | The budget you're syncing to | Paid (YNAB subscription) |
| An [AWS](https://aws.amazon.com/) account | Hosts the small bit of code that does the syncing | Free — this project runs comfortably within AWS's free tier, so it should cost $0/month |

If Node/Yarn, AWS, "Lambda", and "serverless" are all new to you, don't worry — that's exactly what the AWS section
below walks through.

---

### Step 1 — Get the code

Open a terminal and run:

```bash
git clone <this-repo-url>
cd sync-up-bank-to-ynab
yarn
```

`yarn` downloads all the code libraries this project depends on. This can take a minute or two.

---

### Step 2 — Get your Up Bank API key

1. Go to https://api.up.com.au/getting_started.
2. Log in with your Up account and generate a **Personal Access Token**.
3. Copy it somewhere safe for a moment — you'll paste it in a couple of steps.

---

### Step 3 — Get your YNAB API key

1. Go to https://app.youneedabudget.com/settings/developer.
2. Click **New Token**, confirm your password, and copy the token that's shown. YNAB only shows it once, so keep
   it handy.

---

### Step 4 — Set up AWS (the part that trips people up)

**In plain terms:** AWS Lambda is Amazon's way of running a small piece of code on demand, without you having to
own or manage a server. You're not "hosting a website" or "renting a computer" — you're just telling AWS "run this
tiny function whenever Up sends it a notification." AWS only charges you for the (tiny) amount it actually runs,
which for this project is effectively free.

We deploy using a tool called the **Serverless Framework**, which handles the AWS setup for you — you don't need to
click around the AWS Console building things by hand. You just need to give it permission to act on your behalf,
which means creating an AWS account and a set of "access keys."

1. **Create an AWS account** at https://aws.amazon.com/ if you don't already have one. You'll need a credit/debit
   card to sign up (AWS requires this even for free-tier usage), but this project shouldn't incur charges.

2. **Create an IAM user with access keys.** This is a set of credentials that let tools like Serverless act on your
   AWS account without using your main login.
   - In the AWS Console, search for **IAM** and open it.
   - Go to **Users** → **Create user**. Give it a name like `up-ynab-deploy`.
   - Attach the permission **AdministratorAccess** (simplest option for a personal project like this — it lets the
     Serverless Framework create everything it needs).
   - After the user is created, open it, go to the **Security credentials** tab, and click **Create access key**.
     Choose **Command Line Interface (CLI)** as the use case.
   - You'll be shown an **Access Key ID** and a **Secret Access Key**. Copy both now — the secret key is only shown
     once.

3. **Install the AWS CLI** (a command-line tool for talking to AWS) if you don't have it:
   - Mac: `brew install awscli`
   - Otherwise, follow https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html

4. **Tell the AWS CLI your credentials:**
   ```bash
   aws configure
   ```
   It'll ask you for:
   - **AWS Access Key ID** — paste the one from step 2
   - **AWS Secret Access Key** — paste the one from step 2
   - **Default region name** — use `ap-southeast-2` (Sydney) to match this project's default, or your closest AWS
     region
   - **Default output format** — you can just press Enter to leave this blank

That's it — AWS is now set up, and the Serverless Framework will use these credentials automatically when you
deploy in Step 7.

---

### Step 5 — Tell the project which Up accounts map to which YNAB accounts

This is the "which account goes where" configuration.

1. Copy the example file to create your real one:
   ```bash
   cp src/accountMapping.example.json src/accountMapping.json
   ```
   (This file is gitignored — it holds your personal account details and is never committed to the repo.)

2. Open `src/accountMapping.json`. You'll want one entry for:
   - Your Up **transactional** account
   - A **catchall** account (for any Up Saver you don't map individually) — give this one `"upId": "UP_CATCHALL"`
   - Each individual Up **Saver** you want tracked separately in YNAB

   The `name` field is just a label for your own reference — it isn't used by the code.

3. Get your Up account IDs by running (replace `<UP_API_KEY>` with the key from Step 2):
   ```bash
   curl https://api.up.com.au/api/v1/accounts -G -H 'Authorization: Bearer <UP_API_KEY>'
   ```
   This lists all your Up accounts along with their `id`. Copy the relevant `id` into `upId` for each mapping.

4. In YNAB, create an account for each: the Up transactional account, each mapped Saver, and a catchall account.

5. For each YNAB account, open it and look at the URL — it'll look like
   `https://app.youneedabudget.com/<budget-id>/accounts/<account-id>`. Copy the `<account-id>` part into `ynabId`
   for the matching mapping.

---

### Step 6 — Add your secret keys

1. Copy the example env file:
   ```bash
   cp .env.example .env
   ```
   (Also gitignored — never committed.)

2. Open `.env` and fill in:
   - `UP_API_KEY` — from Step 2
   - `YNAB_API_KEY` — from Step 3
   - `YNAB_BUDGET_ID` — open your budget in YNAB, the URL looks like `https://app.youneedabudget.com/<budget-id>` —
     copy the `<budget-id>` part
   - Leave `UP_WEBHOOK_SECRET` blank for now — you'll fill this in during Step 7

---

### Step 7 — Deploy it

1. Run:
   ```bash
   yarn sls deploy
   ```
   This is the Serverless Framework packaging up the code and creating everything it needs in AWS. It can take a
   few minutes the first time.

2. When it finishes, look for a line under `endpoints` that looks like:
   ```
   POST - https://xxxxxx.execute-api.ap-southeast-2.amazonaws.com/prod/webhook/up
   ```
   Copy that whole URL — this is the address Up will send transaction notifications to.

3. Register that address with Up as a webhook (replace `<UP_API_KEY>` and `<ENDPOINT>` with your values):
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

4. The response includes a `secretKey` — copy it into `UP_WEBHOOK_SECRET` in your `.env` file.

5. Deploy one more time so the webhook secret takes effect:
   ```bash
   yarn sls deploy
   ```

You're done! Spend some money on your Up card and watch it land, unapproved, in YNAB.

**Making changes later?** You only need to run `yarn sls deploy` again — no need to repeat the webhook registration.

---

## Troubleshooting

- **"I don't understand what Lambda/Serverless actually created in my AWS account"** — you don't need to. The
  Serverless Framework sets up a Lambda function (the code that runs) and an API Gateway (the URL that Up sends
  notifications to) for you. If you're curious, you can see them by searching "Lambda" or "API Gateway" in the AWS
  Console, but there's nothing you need to configure by hand there.
- **Nothing shows up in YNAB** — double check `src/accountMapping.json` has the right Up/YNAB account IDs, and that
  `UP_WEBHOOK_SECRET` in `.env` matches the `secretKey` from Up's webhook registration response, then redeploy.
- **`aws configure` / deploy fails with a permissions or credentials error** — re-check the Access Key ID/Secret
  from Step 4 were entered correctly, and that the IAM user has the `AdministratorAccess` permission attached.

---

## Personalisation that was stripped out of this repo

This repo started as a personal project, so the following files/values were removed before it was made available
and need to be recreated locally by following the steps above (both are gitignored, so this only needs doing once
per checkout):

- `.env` — real Up/YNAB API keys, webhook secret, and YNAB budget ID. Recreate from `.env.example`.
- `src/accountMapping.json` — real Up account IDs, YNAB account IDs, and account names. Recreate from
  `src/accountMapping.example.json`.

No other personal information (names, emails, tokens) is present anywhere else in the codebase.

## Development

This is a personal backup/fork, not actively looking for outside contributions — but feel free to open an issue if
you spot a bug.
