"""Generates setup-checklist.pdf, the printable companion to the README's setup guide.

Keep this in step with the README whenever the setup steps change, then regenerate:

    pip install reportlab
    python3 scripts/make-setup-checklist.py
"""

import os
import re
import sys

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "setup-checklist.pdf")

PAGE_W, PAGE_H = A4
MARGIN_X = 52
TOP = PAGE_H - 50
BOTTOM = 55
CONTENT_W = PAGE_W - 2 * MARGIN_X

ORANGE = HexColor("#D35400")
TEXT = HexColor("#222222")
MUTED = HexColor("#555555")
FAINT = HexColor("#999999")
RULE = HexColor("#888888")
LIGHT_RULE = HexColor("#DDDDDD")
WARN_FILL = HexColor("#FFF4DC")
WARN_BORDER = HexColor("#E8A33D")
WARN_TEXT = HexColor("#7A4B00")
TABLE_HEAD = HexColor("#EEEEEE")
TABLE_LINE = HexColor("#BBBBBB")

# Each step: (number, title, checklist items, fields, page break before?)
# Items can mark inline code with `backticks`. Fields are (label, hint) and get a line to write on.
STEPS = [
    (1, "Install the tools you need", [
        "Homebrew installed (Mac only)",
        "Node.js installed",
        "Yarn installed",
        "Checked `node --version` and `yarn --version` both work",
        "A text editor installed (e.g. VS Code)",
    ], [], False),
    (2, "Download the code", [
        "Repo downloaded (git clone or ZIP) and unzipped",
        "Folder moved to its long-term home (not Downloads) and opened in text editor",
    ], [], False),
    (3, "Get your Up Bank API key", [
        "Personal Access Token generated at api.up.com.au/getting_started",
    ], [("Up API key", "starts with up:yeah:")], False),
    (4, "Get your YNAB API key", [
        "New Token created at app.ynab.com/settings/developer",
    ], [("YNAB API key", None)], False),
    (5, "Set up AWS", [
        "AWS account created",
        "IAM user created with AdministratorAccess",
        "Access key created for that IAM user",
        "AWS CLI installed",
        "Ran `aws configure` with the access key, secret key, and region",
    ], [
        ("AWS Access Key ID", None),
        ("AWS Secret Access Key", None),
        ("AWS region used", "e.g. ap-southeast-2"),
    ], True),
    (6, "Map Up accounts to YNAB accounts", [
        "accountMapping.json created from the .example file",
        "Up account IDs looked up via the API (matched by displayName)",
        "YNAB account IDs copied from account URLs",
        "Every account (incl. catchall, if used) added to accountMapping.json",
    ], "MAPPING_TABLE", False),
    (7, "Add your secret keys", [
        ".env created from .env.example",
        "UP_API_KEY, YNAB_API_KEY and YNAB_BUDGET_ID filled in",
        "UP_WEBHOOK_SECRET left blank for now",
    ], [("YNAB Budget ID", "from the budget URL")], False),
    (8, "Install dependencies and deploy", [
        "Ran `yarn` to install dependencies",
        "Ran `yarn sls deploy` (upWebhookHandler shows a few hundred kB)",
        "Copied the endpoint URL — just the part from https:// onwards",
        "Registered the webhook with Up via curl (once only)",
        "Copied the secretKey from the response into UP_WEBHOOK_SECRET",
        "Ran `yarn sls deploy` again",
    ], [
        ("Webhook endpoint URL", None),
        ("Webhook ID", "the id straight after \"type\":\"webhooks\""),
        ("Webhook secret (UP_WEBHOOK_SECRET)", None),
    ], True),
]

CHECK_IT_WORKS = [
    "Listed webhooks: exactly one, and its url matches the endpoint URL above",
    "Sent a test ping (with `-d \"\"`)",
    "Newest entry in the delivery log shows \"statusCode\":200",
    "Real test: moved $1 (a transfer, not a card purchase) and it appeared in YNAB",
]


class Sheet:
    def __init__(self, path):
        self.c = canvas.Canvas(path, pagesize=A4)
        self.c.setTitle("Up Bank to YNAB Sync - Setup Checklist")
        self.y = TOP
        self.field_names = set()

    def field_name(self, label):
        """A unique, stable form-field name derived from its label."""
        base = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")
        name, n = base, 2
        while name in self.field_names:
            name, n = f"{base}_{n}", n + 1
        self.field_names.add(name)
        return name

    def text_input(self, name, x, y, width, height, tooltip, font_size=0):
        # Transparent, borderless, so it prints as a plain line/cell. Keys can be long (Up's are ~135
        # characters), so allow plenty; font_size=0 lets the viewer shrink long values to fit.
        self.c.acroForm.textfield(
            name=name, tooltip=tooltip, x=x, y=y, width=width, height=height,
            fillColor=None, borderWidth=0, textColor=TEXT, fontName="Helvetica", fontSize=font_size,
            maxlen=1000, annotationFlags="print",
        )

    def new_page(self):
        self.c.showPage()
        self.y = TOP

    def need(self, h):
        if self.y - h < BOTTOM:
            self.new_page()

    def rich_text(self, x, y, text, size, color):
        """Draw text where `backticks` switch to a monospace font."""
        self.c.setFillColor(color)
        for i, part in enumerate(re.split(r"`", text)):
            font = "Courier" if i % 2 else "Helvetica"
            self.c.setFont(font, size)
            self.c.drawString(x, y, part)
            x += self.c.stringWidth(part, font, size)

    def wrap_lines(self, text, size, font="Helvetica", width=CONTENT_W):
        lines, line = [], ""
        for word in text.split():
            trial = f"{line} {word}".strip()
            if self.c.stringWidth(trial, font, size) > width:
                lines.append(line)
                line = word
            else:
                line = trial
        lines.append(line)
        return lines

    def wrapped(self, text, size, color, font="Helvetica", width=CONTENT_W, x=MARGIN_X, leading=None):
        leading = leading or size * 1.45
        lines = self.wrap_lines(text, size, font, width)
        self.c.setFont(font, size)
        self.c.setFillColor(color)
        for ln in lines:
            self.c.drawString(x, self.y, ln)
            self.y -= leading
        return len(lines) * leading

    def rule(self, color=RULE, gap_after=0):
        self.c.setStrokeColor(color)
        self.c.setLineWidth(0.6)
        self.c.line(MARGIN_X, self.y, PAGE_W - MARGIN_X, self.y)
        self.y -= gap_after

    def header(self):
        c = self.c
        c.setFont("Helvetica", 24)
        c.setFillColor(TEXT)
        title = "Up Bank → YNAB Sync"
        c.drawCentredString(PAGE_W / 2, self.y - 14, title)
        self.y -= 40
        c.setFont("Helvetica", 9)
        c.setFillColor(MUTED)
        c.drawString(MARGIN_X, self.y, "Setup checklist & worksheet")
        self.y -= 18
        self.wrapped(
            "Print this out and tick off each step as you go. Space is included below for the keys and IDs you'll "
            "collect along the way, so you don't have to keep them all in your head. Full instructions for every "
            "step are in the project's README — this sheet is just a companion to it.",
            9.5, MUTED,
        )
        self.y -= 6

        # Warning box: measure the wrapped text, draw the box, then the text on top.
        warn = (
            "This sheet will hold real API keys and secrets once filled in. Treat it like a password: don't "
            "photograph it, leave it out, or leave it lying around once you're finished. Shred it (or securely "
            "dispose of it) once your setup is working and you no longer need to refer back to it. You can also "
            "fill it in on screen and paste keys straight in \u2014 but if you save it, keep it out of synced "
            "folders (Dropbox, iCloud, OneDrive) and delete it once you're done."
        )
        pad = 10
        top = self.y
        box_h = len(self.wrap_lines(warn, 9, width=CONTENT_W - 2 * pad)) * 9 * 1.45 + 2 * pad
        c.setFillColor(WARN_FILL)
        c.setStrokeColor(WARN_BORDER)
        c.setLineWidth(0.8)
        c.rect(MARGIN_X - 6, top - box_h, CONTENT_W + 12, box_h, fill=1, stroke=1)
        self.y = top - pad - 4
        self.wrapped(warn, 9, WARN_TEXT, width=CONTENT_W - 2 * pad, x=MARGIN_X + pad)
        self.y = top - box_h - 10
        self.rule(LIGHT_RULE, gap_after=22)

    def step_title(self, num, title):
        self.need(60)
        c = self.c
        c.setFont("Helvetica", 14)
        c.setFillColor(ORANGE)
        label = f"Step {num}"
        c.drawString(MARGIN_X, self.y, label)
        c.setFillColor(TEXT)
        c.drawString(MARGIN_X + c.stringWidth(label, "Helvetica", 14) + 7, self.y, title)
        self.y -= 22

    def sub_title(self, title):
        self.need(50)
        self.c.setFont("Helvetica-Bold", 11)
        self.c.setFillColor(TEXT)
        self.c.drawString(MARGIN_X, self.y, title)
        self.y -= 20

    def checkbox(self, text):
        self.need(24)
        c = self.c
        c.acroForm.checkbox(
            name=self.field_name("check " + text), tooltip=text.replace("`", ""), x=MARGIN_X, y=self.y - 2, size=10,
            buttonStyle="check", borderColor=TEXT, fillColor=None, textColor=TEXT, borderWidth=0.8,
            fieldFlags="", annotationFlags="print", forceBorder=True,
        )
        self.rich_text(MARGIN_X + 25, self.y, text, 9.5, TEXT)
        self.y -= 24

    def field(self, label, hint):
        self.need(36)
        c = self.c
        c.setFont("Helvetica", 9)
        c.setFillColor(MUTED)
        c.drawString(MARGIN_X, self.y, label)
        if hint:
            x = MARGIN_X + c.stringWidth(label, "Helvetica", 9) + 4
            c.setFont("Helvetica", 7.5)
            c.setFillColor(FAINT)
            c.drawString(x, self.y, f"({hint})")
        # Keys and IDs shrink to fit; anything with a short example value (e.g. the region) stays a normal size.
        size = 10 if hint and hint.startswith("e.g.") else 0
        self.text_input(self.field_name(label), MARGIN_X, self.y - 20, CONTENT_W, 14, label, size)
        self.y -= 22
        self.rule(gap_after=14)

    def mapping_table(self, rows=5):
        cols = [("Account name", 0.27), ("Up account ID", 0.36), ("YNAB account ID", 0.37)]
        row_h = 20
        x0 = MARGIN_X + 8
        w = CONTENT_W - 8
        self.need(row_h * (rows + 1) + 10)
        c = self.c
        top = self.y + 4
        c.setFillColor(TABLE_HEAD)
        c.rect(x0, top - row_h, w, row_h, fill=1, stroke=0)
        c.setStrokeColor(TABLE_LINE)
        c.setLineWidth(0.6)
        for r in range(rows + 2):
            c.line(x0, top - r * row_h, x0 + w, top - r * row_h)
        x = x0
        c.setFont("Helvetica", 8.5)
        c.setFillColor(TEXT)
        for name, frac in cols:
            c.line(x, top, x, top - (rows + 1) * row_h)
            c.drawString(x + 6, top - row_h + 7, name)
            x += w * frac
        c.line(x0 + w, top, x0 + w, top - (rows + 1) * row_h)
        for r in range(1, rows + 1):
            x = x0
            for name, frac in cols:
                cell_w = w * frac
                self.text_input(
                    self.field_name(f"{name} row {r}"), x + 2, top - (r + 1) * row_h + 2, cell_w - 4, row_h - 4,
                    f"{name} (row {r})", 9 if name == "Account name" else 0,
                )
                x += cell_w
        self.y = top - (rows + 1) * row_h - 36

    def footer_note(self):
        self.need(40)
        self.y -= 4
        self.rule(LIGHT_RULE, gap_after=16)
        self.c.setFont("Helvetica", 8.5)
        self.c.setFillColor(MUTED)
        self.c.drawString(
            MARGIN_X + 4, self.y,
            "Full step-by-step instructions, troubleshooting, and explanations for everything above are in the "
            "project's README.md.",
        )

    def save(self):
        self.c.save()


def main():
    s = Sheet(OUT)
    s.header()
    for num, title, items, fields, break_before in STEPS:
        if break_before:
            s.new_page()
        s.step_title(num, title)
        for item in items:
            s.checkbox(item)
        if fields == "MAPPING_TABLE":
            s.mapping_table()
        else:
            for label, hint in fields:
                s.field(label, hint)
            s.y -= 8
    s.sub_title("Check it's working")
    for item in CHECK_IT_WORKS:
        s.checkbox(item)
    s.footer_note()
    s.save()
    print(f"Wrote {os.path.normpath(OUT)}")


if __name__ == "__main__":
    main()
