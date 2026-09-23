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

**Prefer working on paper?** [setup-checklist.pdf](setup-checklist.pdf) is a printable A4 checklist covering every
step below, with space to jot down each key/ID as you collect it. It holds real secrets once filled in, so shred it
once you're done setting up.

### What you'll need before you start

| Thing                                     | What it's for                                     | Cost                                                                                    |
| ----------------------------------------- | ------------------------------------------------- | --------------------------------------------------------------------------------------- |
| A Mac or Windows computer                 | To run the setup commands                         | —                                                                                       |
| An [Up Bank](https://up.com.au) account   | The bank you're syncing from                      | Free                                                                                    |
| A [YNAB](https://www.ynab.com/) account   | The budget you're syncing to                      | Paid (YNAB subscription)                                                                |
| An [AWS](https://aws.amazon.com/) account | Hosts the small bit of code that does the syncing | Free — this project runs comfortably within AWS's free tier, so it should cost $0/month |

You do **not** need to already have Node.js or Yarn installed — Step 1 below installs them from scratch. If
"Lambda" and "serverless" are unfamiliar terms, don't worry, that's exactly what Step 5 walks through.

This guide keeps the terminal to a minimum — you'll only use it for one-off tool installs, a few quick API lookups
(copy-paste commands where you just fill in your own key or ID), and the deploy step. All the file editing
(downloading the code, filling in your account details) is done in Finder/File Explorer and a regular text editor
instead, since that's a much easier way to work with files if you're not used to a terminal.

**Anything in `<ANGLE_BRACKETS>` is a placeholder.** Replace the whole thing, brackets included, with your own
value — e.g. `Bearer <UP_API_KEY>` becomes `Bearer up:yeah:abc123...`. Everything else in a command stays exactly
as written, including the double quotes.

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

**If the Homebrew install fails with a permissions error**, or `brew install` fails even though Homebrew is already
installed, it's usually one of two things:

- You're not an administrator on this Mac (Homebrew needs to create/own `/opt/homebrew` or `/usr/local`, which
  requires admin rights) — common on work-managed machines.
- Homebrew was previously installed using `sudo`, which leaves those folders owned by `root` instead of you.

If you're not an admin on the Mac, Homebrew isn't installable at all, but you can still get Node.js without it (and
without `sudo`) using [nvm](https://github.com/nvm-sh/nvm), which installs entirely into your home folder — follow
its install instructions, then run `nvm install --lts` to get Node, and `corepack enable` to get Yarn.

**You'll also want a text editor** for the config files you'll edit in a couple of steps (not writing code, just
filling in values). If you don't already have one, install [VS Code](https://code.visualstudio.com/) (free, Mac and
Windows) — plain text editors like TextEdit (Mac) or Notepad (Windows) work too, just avoid anything that
auto-formats text like Word or Pages.

---

### Step 2 — Download the code

Before you start, decide where this project folder is going to live long-term (e.g. a folder in your
**Documents**) — you'll be coming back into it for every step below, and again in future whenever you want to make
changes or redeploy, so it's worth settling its home now rather than moving it around later.

**If you're comfortable with a couple of terminal commands**, `git clone`-ing the repo instead of downloading a ZIP
means you can later pull future updates with `git pull` instead of re-downloading and manually redoing your setup.
In your terminal, navigate to wherever you want the project folder to live, then run:

```bash
git clone https://github.com/grantsteele/sync-up-bank-to-ynab.git
```

**Otherwise, downloading a ZIP works fine too** — you just won't have an easy way to pick up future changes:

1. Open the repo in your browser.
2. Click the green **Code** button, then **Download ZIP**.
3. Find the downloaded ZIP (usually in your **Downloads** folder) and extract/unzip it. On Mac, just double-click
   it. On Windows, right-click it and choose **Extract All...**.
4. Move the extracted folder to the place you decided on above (e.g. your **Documents** folder) — not somewhere
   temporary like Downloads, since this is where the project will stay.

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

1. Go to https://app.ynab.com/settings/developer.
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

     | Region code      | Location           |
     | ---------------- | ------------------ |
     | `ap-southeast-2` | Sydney             |
     | `us-east-1`      | N. Virginia, USA   |
     | `us-west-2`      | Oregon, USA        |
     | `eu-west-1`      | Ireland            |
     | `eu-central-1`   | Frankfurt, Germany |
     | `ap-southeast-1` | Singapore          |
     | `ap-south-1`     | Mumbai, India      |

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
     account you _haven't_ mapped individually, so it's a safety net for accounts you open later or forget to add.
     **You can skip this entry entirely if you're going to map every single Up account you have individually** —
     just remember any new Up Saver you open in future will need its own entry added, since there won't be a
     catchall to fall back to.

   The `name` field is just a label for your own reference — it isn't used by the code.

3. Get your Up account IDs. Open a terminal (Mac: **Terminal**; Windows: **Command Prompt** — not PowerShell) and
   run this, replacing `<UP_API_KEY>` with your key from Step 3:

   ```bash
   curl https://api.up.com.au/api/v1/accounts -g -G -d "page[size]=100" -H "Authorization: Bearer <UP_API_KEY>"
   ```

   You'll get back one long block of text covering every account you have with Up. Each account in it looks like
   this (trimmed down):

   ```
   {"type":"accounts","id":"1a2b3c4d-1234-5678-9abc-def012345678","attributes":{"displayName":"Spending","accountType":"TRANSACTIONAL",...
   ```

   `displayName` is the account's name as shown in the Up app (your main account is called "Spending"), and the
   `id` just before it is what goes into `upId`. It's easiest to paste the whole output into your text editor and
   search for `displayName` to step through each account.

4. In YNAB, you need an account for each mapping: the Up transactional account, each mapped Saver, and the catchall
   (if you're using one). If you've already got matching YNAB accounts set up (e.g. from manually tracking these
   before), you don't need to create new ones — just use your existing accounts in the next step.

   Several mappings can point at the **same** YNAB account if you'd rather not track them separately — e.g. giving
   the catchall the same `ynabId` as your transactional account, so everything you haven't mapped individually lands
   there. If you do this, keep in mind:

   - Transfers between two Up accounts that share a YNAB account won't appear in YNAB at all. That's deliberate —
     the money never left that YNAB account, so its balance is still right — but it can look like a transfer went
     missing.
   - That YNAB account's balance will be the combined total of all the Up accounts pointing at it, so it won't match
     any single balance in the Up app.

5. For each YNAB account, open it in YNAB in your web browser and look at the address bar — it'll look like
   `https://app.ynab.com/<budget-id>/accounts/<account-id>`. Copy the `<account-id>` part (everything after
   `/accounts/`) into `ynabId` for the matching mapping.

   When you're done, your `accountMapping.json` should look something like this — one `{ ... }` block per mapping,
   separated by commas, with no comma after the last one:

   ```json
   [
     {
       "name": "Up Spending",
       "upId": "1a2b3c4d-1234-5678-9abc-def012345678",
       "ynabId": "9f8e7d6c-1234-5678-9abc-def012345678"
     },
     {
       "name": "Up Catchall",
       "upId": "UP_CATCHALL",
       "ynabId": "5a6b7c8d-1234-5678-9abc-def012345678"
     }
   ]
   ```

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
   - `YNAB_BUDGET_ID` — open your budget in YNAB in your web browser; the address bar will show something like
     `https://app.ynab.com/<budget-id>/budget` — copy the `<budget-id>` part (the long string straight after
     `app.ynab.com/`)
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

4. When it finishes, look for a line starting with `endpoint:` that looks like:

   ```
   endpoint: POST - https://xxxxxx.execute-api.ap-southeast-2.amazonaws.com/prod/webhook/up
   ```

   Copy just the URL — starting from `https://` and ending with `/webhook/up`. **Don't** include the
   `endpoint: POST - ` part in front of it. This is the address Up will send transaction notifications to.

   Just above it, the `upWebhookHandler` line should show a size of a few hundred kB. If it's tiny (tens of kB),
   you're running an old copy of this project whose deploys leave out the code's libraries — see the "`502`"
   entry in [Troubleshooting](#troubleshooting).

5. Register that address with Up as a webhook. This is one long command — paste it into your terminal as a single
   line. Replace `<UP_API_KEY>` with your Up key and `<ENDPOINT>` with the URL from the previous step, and leave
   all the `\"` characters exactly as they are:

   ```bash
   curl https://api.up.com.au/api/v1/webhooks -X POST -H "Authorization: Bearer <UP_API_KEY>" -H "Content-Type: application/json" -d "{\"data\":{\"attributes\":{\"url\":\"<ENDPOINT>\",\"description\":\"Prod YNAB webhook\"}}}"
   ```

   Only run this once — running it again registers a second webhook, and you'll get every transaction twice. (Not
   sure if it worked? Use the "list your webhooks" command [below](#check-its-working) to check before trying
   again.)

6. The response will look something like this (trimmed down):

   ```
   {"data":{"type":"webhooks","id":"7e6d5c4b-1234-5678-9abc-def012345678","attributes":{"url":"https://...","description":"Prod YNAB webhook","secretKey":"AbCdEf123...",...
   ```

   Two values in it matter:

   - **`secretKey`** — copy this into `UP_WEBHOOK_SECRET` in your `.env` file (back in your text editor). This is
     the only time Up will ever show it to you.
   - **`id`** (the one straight after `"type":"webhooks"`) — this is your **webhook ID**. You don't need it for
     setup, but it's handy to note down: the testing and removal commands later in this guide ask for it as
     `<WEBHOOK_ID>`. If you lose it, you can always look it up again [below](#check-its-working).

   If the response instead starts with `{"errors":`, the registration didn't work — see
   [Troubleshooting](#troubleshooting).

7. Deploy one more time so the webhook secret takes effect:
   ```bash
   yarn sls deploy
   ```

You're done! Spend some money on your Up card and it'll land, unapproved, in YNAB.

**Card purchases don't appear straight away.** When you tap your card, Up first records the purchase as _pending_
(Up calls this "held"). This project deliberately waits until the purchase **settles** before adding it to YNAB —
usually 1–3 days for card purchases — so it doesn't create a duplicate when the final amount comes through.
Transfers and payments that settle instantly show up within seconds. So if you've just bought a coffee to test it,
don't worry if it isn't in YNAB yet.

#### Check it's working

You don't have to wait for a real transaction to test it — you can ask Up to send a test "ping" to your webhook.

**1. List your webhooks** to find your webhook ID and check the address Up has on file:

```bash
curl https://api.up.com.au/api/v1/webhooks -H "Authorization: Bearer <UP_API_KEY>"
```

You should get back something like this (trimmed down):

```
{"data":[{"type":"webhooks","id":"7e6d5c4b-1234-5678-9abc-def012345678","attributes":{"url":"https://xxxxxx.execute-api.ap-southeast-2.amazonaws.com/prod/webhook/up","description":"Prod YNAB webhook",...
```

- Your **webhook ID** is the `id` straight after `"type":"webhooks"` — in this example,
  `7e6d5c4b-1234-5678-9abc-def012345678`. It's the same ID from Step 8.6. Don't mix it up with your Up account IDs
  from Step 6 — they look similar, but those identify your bank accounts, not the webhook.
- Check the `url` exactly matches the endpoint from Step 8.4.
- If you get `"data":[]` instead, no webhook is registered — go back and do Steps 8.5–8.7.
- If there's more than one entry, you've registered more than once — see [Troubleshooting](#troubleshooting).

**2. Send a test ping**, replacing `<WEBHOOK_ID>` with your webhook ID:

```bash
curl -X POST https://api.up.com.au/api/v1/webhooks/<WEBHOOK_ID>/ping -H "Authorization: Bearer <UP_API_KEY>"
```

**3. Check whether it got through** by looking at the webhook's delivery log:

```bash
curl https://api.up.com.au/api/v1/webhooks/<WEBHOOK_ID>/logs -H "Authorization: Bearer <UP_API_KEY>"
```

Look for `"statusCode"` in the newest entry (the first one listed): `200` means everything's connected properly.
`403` means `UP_WEBHOOK_SECRET` in your `.env` doesn't match the `secretKey` from Step 8.6 — fix it and run
`yarn sls deploy` again.

**For more detail**, you can look at the function's own logs: in the AWS Console, search for **CloudWatch**, go to **Log groups**,
and open the one named `/aws/lambda/up-bank-ynab-transformer-prod-upWebhookHandler`. Every time Up sends a webhook
notification, a new log entry appears here. Each one starts with a `Webhook: {...}` line showing what Up sent — the
line after it tells you what happened:

| Log line                                                                | What it means                                                                                                      |
| ----------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `Skipping HELD transaction`                                             | Working as intended — the purchase is still pending and will appear in YNAB once it settles.                       |
| `Invalid signature`                                                     | `UP_WEBHOOK_SECRET` in `.env` doesn't match the `secretKey` from Step 8.6. Fix it and run `yarn sls deploy` again. |
| `Creating transaction` / `Updating transaction` followed by `YNAB save` | It's been sent to YNAB — look for it (unapproved) in the account you mapped.                                       |
| `Skipping negative side of internal transfer`                           | Expected — for transfers between your own Up accounts, only one side is sent to YNAB, and YNAB creates the other.  |
| An error mentioning YNAB (e.g. `404` or `401`)                          | Check `YNAB_API_KEY` and `YNAB_BUDGET_ID` in `.env`, and the `ynabId` values in `accountMapping.json`.             |

Note that the **Test** button in the Lambda section of the AWS Console isn't a useful check — it runs the function
directly without involving Up, so it doesn't tell you whether your webhook is set up correctly. Use the ping above
instead.

**Making changes later?** Edit `.env` or `src/accountMapping.json`, then run `yarn sls deploy` again — no need to
repeat the webhook registration.

---

## Troubleshooting

- **"I don't understand what Lambda/Serverless actually created in my AWS account"** — you don't need to. The
  Serverless Framework sets up a Lambda function (the code that runs) and an API Gateway (the URL that Up sends
  notifications to) for you. If you're curious, you can see them by searching "Lambda" or "API Gateway" in the AWS
  Console, but there's nothing you need to configure by hand there.
- **A `curl` command gives `Not Authorized`, `Could not resolve host`, or a `Port number` error** — the command's
  quotes got mangled, so your API key never reached Up. Make sure you're using the
  double quotes (`"`) exactly as shown in this guide — not single quotes (`'`), which Windows Command Prompt doesn't
  understand, and not "smart" curly quotes (`“ ”`), which some apps swap in when you copy and paste. On Windows,
  use Command Prompt rather than PowerShell. Also check the key comes straight after `Bearer ` with a single space.
- **Not sure whether the webhook was ever registered** — run the "list your webhooks" command from
  [Check it's working](#check-its-working). If it returns `"data":[]`, nothing is registered — redo Steps 8.5–8.7.
  If there's already an entry, check its `url` is correct rather than registering another one.
- **"What's my webhook ID?"** — see step 1 of [Check it's working](#check-its-working).
- **I registered the webhook more than once / transactions are coming through twice** — list your webhooks, then
  delete the extras with the delete command from [Starting over or uninstalling](#starting-over-or-uninstalling)
  (step 2), keeping only the one whose `secretKey` is in your `.env`. You can't see a webhook's `secretKey` after
  it's created, so if you're not sure which one that is, delete them all, redo Steps 8.5–8.7, and you'll end up
  with exactly one.
- **I registered the wrong URL** — webhooks can't be edited. Delete it (as above) and register it again with the
  right URL (Steps 8.5–8.7).
- **The webhook delivery log shows `"statusCode":502`** — the function is crashing before it can respond. The
  most common cause is an old copy of this project: its deploys left out the libraries the code needs when used
  with newer versions of npm, so the function crashes as soon as it runs. Get the latest version of the project
  (`git pull`, or download the ZIP again and copy your `.env` and `src/accountMapping.json` into it), then run
  `yarn` and `yarn sls deploy`. Your endpoint URL and webhook stay the same, so there's no need to re-register
  anything. If it still happens, the CloudWatch logs (see [Check it's working](#check-its-working)) will show the
  actual error.
- **Card purchases aren't showing up** — they won't until they settle, usually 1–3 days later. See the note after
  Step 8.7.
- **Nothing shows up in YNAB** — double check `src/accountMapping.json` has the right Up/YNAB account IDs, and that
  `UP_WEBHOOK_SECRET` in `.env` matches the `secretKey` from Up's webhook registration response, then redeploy.
- **`aws configure` / deploy fails with a permissions or credentials error** — re-check the Access Key ID/Secret
  from Step 5 were entered correctly, and that the IAM user has the `AdministratorAccess` permission attached.
- **A command says "command not found" or "not recognized"** — close and reopen your terminal/command prompt so it
  picks up the newly installed tools, then try again.
- **Deploy fails with a `Stack already exists` or other CloudFormation error** — this usually means a previous
  deploy was interrupted partway through. Run `yarn sls remove` to tear down the partial deployment, then
  `yarn sls deploy` again.
- **The webhook was registered but nothing ever arrives** — first check the CloudWatch log group described in
  [Check it's working](#check-its-working).
  If it's empty even after a transaction happens, double-check the `url` you registered with Up in Step 8.5 exactly
  matches the endpoint AWS gave you — it should start with `https://` and end with `/webhook/up`, with no
  `POST - ` in front and no trailing slash (the "list your webhooks" command shows what Up has on file). If
  entries do appear there but error out, the issue is in the account mapping or webhook secret — see the "Nothing
  shows up in YNAB" entry above.

---

## Starting over or uninstalling

**Just trying to fix something?** You probably don't need to start over. Edit `.env` or `src/accountMapping.json`
and run `yarn sls deploy` again from the same folder — it updates your existing setup in place and keeps the same
URL, so your Up webhook keeps working.

**To remove everything** (or tear it down before setting it up again from scratch), do these in order.

**Deleting the project folder on its own doesn't remove anything from AWS** — your function keeps running and Up
keeps sending it notifications.

1. **Remove everything from AWS.** Open a terminal inside the project folder (same as Step 8.1) and run:

   ```bash
   yarn sls remove
   ```

   This deletes everything the deploy created: the Lambda function, the webhook URL, its CloudWatch logs, and the
   storage AWS used for deploying. It needs the project folder to still exist, so do this before deleting it.

   _Already deleted the folder?_ Do it in the AWS Console instead: search for **CloudFormation**, check the region in
   the top-right matches the one you deployed to (Sydney, unless you changed it), select the
   `up-bank-ynab-transformer-prod` stack, and click **Delete**.

2. **Delete the webhook from Up**, so Up stops trying to send notifications to a URL that no longer exists. Get its
   webhook ID with the "list your webhooks" command from [Check it's working](#check-its-working), then run:

   ```bash
   curl -X DELETE https://api.up.com.au/api/v1/webhooks/<WEBHOOK_ID> -H "Authorization: Bearer <UP_API_KEY>"
   ```

   Run the "list your webhooks" command again afterwards — it should return `"data":[]`.

3. **Delete the project folder.** If you're going to set it up again, first save a copy of `.env` and
   `src/accountMapping.json` somewhere safe — they hold all your keys and IDs, and you can drop them straight into
   the fresh copy instead of redoing Steps 6 and 7. (Clear out `UP_WEBHOOK_SECRET` in the saved `.env`, though — the
   new webhook you register will come with a new one.) These files contain real API keys, so delete that copy once
   you're done.

**These don't need removing** if you're setting up again:

- Your AWS account, IAM user and `aws configure` credentials — reuse them as-is. (If you're uninstalling for good
  and want to tidy up, you can delete the IAM user from Step 5 in the AWS Console under **IAM → Users**.)
- Your Up and YNAB API keys — these keep working. (Uninstalling for good? You can revoke the YNAB one under
  **Account Settings → Developer Settings** in YNAB, and generate a new Up one at
  [api.up.com.au](https://api.up.com.au) to invalidate the old one.)
- Transactions already imported into YNAB — they stay where they are. If any come through again after you set it
  back up, they're recognised as duplicates and skipped.

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

This is a personal backup/fork, not actively looking for outside contributions. Bug reports are welcome via
GitHub issues, but please note I'm not able to provide setup support — the guide above is as much help as I can
offer.
