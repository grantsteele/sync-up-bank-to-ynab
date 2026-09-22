# Sync Up Bank to YNAB

Automatically syncs [Up Bank](https://up.com.au) transactions into [YNAB](https://www.ynab.com/) — no manual
importing, ever again.

This is a fork of [daveallie/up-bank-ynab-transformer](https://github.com/daveallie/up-bank-ynab-transformer),
maintained independently with a few behavioural changes on top of the original (see [CHANGES.md](CHANGES.md)).

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
| A Mac or Windows computer | To run the setup commands | — |
| An [Up Bank](https://up.com.au) account | The bank you're syncing from | Free |
| A [YNAB](https://www.ynab.com/) account | The budget you're syncing to | Paid (YNAB subscription) |
| An [AWS](https://aws.amazon.com/) account | Hosts the small bit of code that does the syncing | Free — this project runs comfortably within AWS's free tier, so it should cost $0/month |

You do **not** need to already have Node.js or Yarn installed — Step 1 below installs them from scratch. If
"Lambda" and "serverless" are unfamiliar terms, don't worry, that's exactly what Step 5 walks through.

This guide keeps the terminal to a minimum — you'll only use it for one-off tool installs, a couple of quick API
lookups (copy-paste commands, no editing involved), and the final deploy step. All the file editing (downloading
the code, filling in your account details) is done in Finder/File Explorer and a regular text editor instead, since
that's a much easier way to work with files if you're not used to a terminal.

---

### Step 1 — Install the tools you need

These are one-off installs. If you already have one of these, you can skip it.

**On a Mac:**

1. Install **Homebrew** (a package installer for Mac) by opening the **Terminal** app and running:
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```
   Follow any on-screen instructions it gives you (it may ask you to run one or two more commands to finish
   adding it to your PATH — copy and run whatever it prints).
2. Use it to install Node.js and Yarn:
   ```bash
   brew install node yarn
   ```

**On Windows:**

1. Install **Node.js** from https://nodejs.org/ — download the "LTS" version installer and click through it with
   the default options.
2. Open **Command Prompt** (search for it in the Start menu) and install Yarn:
   ```bash
   npm install -g yarn
   ```

**Check it worked** (Mac Terminal or Windows Command Prompt):

```bash
node --version
yarn --version
```

Each command should print a version number. If either says "command not found," close and reopen your
terminal/command prompt and try again — sometimes a restart is needed for the new tools to be recognised.

**You'll also want a text editor** for the config files you'll edit in a couple of steps (not writing code, just
filling in values). If you don't already have one, install [VS Code](https://code.visualstudio.com/) (free, Mac and
Windows) — plain text editors like TextEdit (Mac) or Notepad (Windows) work too, just avoid anything that
auto-formats text like Word or Pages.

---

### Step 2 — Download the code

1. Open the repo in your browser.
2. Click the green **Code** button, then **Download ZIP**.
3. Find the downloaded ZIP (usually in your **Downloads** folder) and extract/unzip it. On Mac, just double-click
   it. On Windows, right-click it and choose **Extract All...**.
4. Move the extracted folder somewhere you'll remember, e.g. your **Desktop** — you'll be going back into it in
   every step from here on.

Now open that folder in your text editor so you can browse and edit its files:

- **VS Code**: go to **File → Open Folder** (Mac: **File → Open...**) and select the folder.
- **TextEdit/Notepad**: you'll instead open individual files directly from Finder/File Explorer as you go —
  right-click a file → **Open With** → your editor.

Once it's open in VS Code, you'll see a file/folder list down the left-hand side — that's how you'll get to
`src/accountMapping.json` and `.env` in later steps.

---

### Step 3 — Get your Up Bank API key

1. Go to https://api.up.com.au/getting_started.
2. Log in with your Up account and generate a **Personal Access Token**.
3. Copy it somewhere safe for a moment — you'll paste it in a couple of steps.

---

### Step 4 — Get your YNAB API key

1. Go to https://app.youneedabudget.com/settings/developer.
2. Click **New Token**, confirm your password, and copy the token that's shown. YNAB only shows it once, so keep
   it handy.

---

### Step 5 — Set up AWS (the part that trips people up)

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
   - **Default region name** — this just picks which AWS data centre your code runs in; pick whichever is closest
     to you for the best performance, or use `ap-southeast-2` (Sydney) to match this project's default. Some
     common ones:

     | Region code | Location |
     |---|---|
     | `ap-southeast-2` | Sydney |
     | `us-east-1` | N. Virginia, USA |
     | `us-west-2` | Oregon, USA |
     | `eu-west-1` | Ireland |
     | `eu-central-1` | Frankfurt, Germany |
     | `ap-southeast-1` | Singapore |
     | `ap-south-1` | Mumbai, India |

     For the full list, see AWS's [Regions and Zones reference](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-regions-availability-zones.html#concepts-available-regions).
   - **Default output format** — you can just press Enter to leave this blank

That's it — AWS is now set up, and the Serverless Framework will use these credentials automatically when you
deploy in Step 8.

---

### Step 6 — Tell the project which Up accounts map to which YNAB accounts

This is the "which account goes where" configuration.

1. In the `src` folder, find `accountMapping.example.json`. Make a copy of it in the same folder (Mac Finder:
   right-click → **Duplicate**; Windows Explorer: right-click → **Copy**, then **Paste**), and rename the copy to
   `accountMapping.json` — i.e. just remove `.example` from the name. In VS Code you can instead right-click the
   file in the sidebar and choose **Copy**, then **Paste**, then rename it.

   (This file is gitignored — it holds your personal account details and is never committed to the repo, so keeping
   `accountMapping.json` as a separate file from the `.example` one matters.)

2. Open `accountMapping.json` in your text editor (in VS Code, it'll be in the `src` folder in the sidebar on
   the left). You'll want one entry for:
   - Your Up **transactional** account
   - Each individual Up **Saver** you want tracked separately in YNAB
   - A **catchall** account — give this one `"upId": "UP_CATCHALL"`. This is where transactions land for any Up
     account you *haven't* mapped individually, so it's a safety net for accounts you open later or forget to add.
     **You can skip this entry entirely if you're going to map every single Up account you have individually** —
     just remember any new Up Saver you open in future will need its own entry added, since there won't be a
     catchall to fall back to.

   The `name` field is just a label for your own reference — it isn't used by the code.

3. Get your Up account IDs by running (replace `<UP_API_KEY>` with the key from Step 3):
   ```bash
   curl https://api.up.com.au/api/v1/accounts -G -H 'Authorization: Bearer <UP_API_KEY>'
   ```
   This lists all your Up accounts along with their `id`. Copy the relevant `id` into `upId` for each mapping.

4. In YNAB, you need an account for each mapping: the Up transactional account, each mapped Saver, and the catchall
   (if you're using one). If you've already got matching YNAB accounts set up (e.g. from manually tracking these
   before), you don't need to create new ones — just use your existing accounts in the next step.

5. For each YNAB account, open it and look at the URL — it'll look like
   `https://app.youneedabudget.com/<budget-id>/accounts/<account-id>`. Copy the `<account-id>` part into `ynabId`
   for the matching mapping.

---

### Step 7 — Add your secret keys

1. In the project's top-level folder, find `.env.example` and make a copy of it named `.env` (also gitignored —
   never committed). Files starting with a dot are treated as "hidden" by Mac/Windows, which makes copying them in
   Finder/File Explorer fiddly, so it's easiest to do this from your text editor instead:
   - **VS Code**: open `.env.example`, then use **File → Save As...**, and save it as `.env` in the same folder
     (just change the filename, don't change the folder).
   - **TextEdit/Notepad**: open `.env.example`, use **Save As...**, and save as `.env` in the same folder — on
     Windows, make sure "Save as type" is set to **All Files** so it doesn't add a `.txt` on the end.

   You should now have both `.env.example` (leave this one alone) and `.env` (this is the one you'll edit) in the
   same folder.

2. Open `.env` in your text editor and fill in:
   - `UP_API_KEY` — from Step 3
   - `YNAB_API_KEY` — from Step 4
   - `YNAB_BUDGET_ID` — open your budget in YNAB, the URL looks like `https://app.youneedabudget.com/<budget-id>` —
     copy the `<budget-id>` part
   - Leave `UP_WEBHOOK_SECRET` blank for now — you'll fill this in during Step 8

---

### Step 8 — Install dependencies and deploy

All your editing is done — this last step needs the terminal again, just to run a couple of commands.

1. Open a terminal/command prompt **inside the project folder** (rather than opening a blank one and typing `cd`):
   - **Mac**: right-click the project folder → **Services → New Terminal at Folder**. If you don't see that
     option, open Terminal normally and drag the project folder from Finder onto the Terminal window — it'll fill
     in the full path for you — then press Enter.
   - **Windows**: open the project folder in File Explorer, click the address bar, type `cmd`, and press Enter.

2. Install the project's dependencies:
   ```bash
   yarn
   ```
   This can take a minute or two.

3. Deploy:
   ```bash
   yarn sls deploy
   ```
   This is the Serverless Framework packaging up the code and creating everything it needs in AWS. It can take a
   few minutes the first time.

4. When it finishes, look for a line under `endpoints` that looks like:
   ```
   POST - https://xxxxxx.execute-api.ap-southeast-2.amazonaws.com/prod/webhook/up
   ```
   Copy that whole URL — this is the address Up will send transaction notifications to.

5. Register that address with Up as a webhook (replace `<UP_API_KEY>` and `<ENDPOINT>` with your values):
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

6. The response includes a `secretKey` — copy it into `UP_WEBHOOK_SECRET` in your `.env` file (back in your text
   editor).

7. Deploy one more time so the webhook secret takes effect:
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
  from Step 5 were entered correctly, and that the IAM user has the `AdministratorAccess` permission attached.
- **A command says "command not found" or "not recognized"** — close and reopen your terminal/command prompt so it
  picks up the newly installed tools, then try again.

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
