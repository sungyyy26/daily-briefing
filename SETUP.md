# Sales Pulse: full setup guide

A free, Google-login-only dashboard for Boosters, fed by Meta Ads, Amazon (AX DB), Notion and Slack.

```
 GitHub Actions (hourly) ── Meta API ──┐
 AX server cron ─────────── MySQL ─────┼──► /api/ingest ──► Cloudflare KV ──► /api/data ──► Dashboard
 GitHub Actions ─────────── Notion API ┘                                         ▲
 Slack alerts (later) ◄── reads /api/data                        Cloudflare Access (Google login, @boosters.kr only)
```

**Cost:** $0, except AI chat (Anthropic API, pay per use, about a few $/month).
**Time:** about 1.5 hours total. Do the parts in order. Each part ends with a ✅ check.

**Before you start**, have these ready:
- GitHub account `sungyyy26`
- Your Meta System User token
- A Google Workspace admin (or yourself, if you are one) for the Google login step
- SSH access to the AX server
- A notes app open to save values. You'll collect:
  `INGEST_TOKEN`, `ANTHROPIC_API_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `NOTION_TOKEN`, `SLACK_BOT_TOKEN`

> Never paste tokens into code files or GitHub issues. The repo is **public**. Tokens only go into Cloudflare/GitHub **secret** fields or the AX server's `.env`.

---

## Part 1: Get the code onto `main` (5 min)

1. Open **github.com/sungyyy26/daily-briefing**.
2. Click **Pull requests → New pull request**.
3. Set **base: main** and **compare: ccr-1e9e3c88-ld36wi**, then click **Create pull request → Merge pull request → Confirm merge**.
4. On your laptop:
   ```
   git clone https://github.com/sungyyy26/daily-briefing.git   # first time
   cd daily-briefing && git checkout main && git pull           # every time after
   ```
✅ You see `public/`, `functions/`, `sync/`, `ax_sync/` folders on `main`.

## Part 2: Create the ingest password (1 min)

This is a shared secret that lets GitHub and the AX server send data to your site.
- Mac/Linux terminal: `openssl rand -hex 32`
- Windows PowerShell: `-join ((48..57)+(97..102) | Get-Random -Count 64 | % {[char]$_})`

Save the result as **INGEST_TOKEN**.

## Part 3: Anthropic API key for AI chat (5 min)

1. Go to **console.anthropic.com** and sign in.
2. **Settings → Billing**: add a card, buy $10 credit, and set a monthly limit (e.g. $20) under **Limits**.
3. **API Keys → Create Key**, name it `sales-pulse`, and copy it (`sk-ant-…`). Save as **ANTHROPIC_API_KEY**.

## Part 4: Cloudflare Pages site (10 min)

1. Sign up at **dash.cloudflare.com** (Free plan).
2. Left menu **Workers & Pages → Create → Pages tab → Import an existing Git repository**.
3. **Connect GitHub**, choose **Only select repositories → daily-briefing → Install & Authorize**.
4. Select `daily-briefing` → **Begin setup**:

   | Field | Value |
   |---|---|
   | Project name | `boosters-sales-pulse` |
   | Production branch | `main` |
   | Framework preset | None |
   | Build command | *(empty)* |
   | Build output directory | `public` |

5. **Save and Deploy.** Wait for "Success". Your URL is `https://boosters-sales-pulse.pages.dev`.

✅ Opening the URL shows the dashboard with "Couldn't load data" (normal for now).

## Part 5: Storage and secrets (5 min)

1. Left menu **Storage & Databases → KV → Create namespace**, name it `sales-pulse`, then **Add**.
2. **Workers & Pages → boosters-sales-pulse → Settings → Bindings → Add → KV namespace**:
   - Variable name: `SALES` (exactly), KV namespace: `sales-pulse` → **Save**.
3. **Settings → Variables and Secrets → Add**, one at a time, Type = **Secret**:
   - `INGEST_TOKEN` = value from Part 2
   - `ANTHROPIC_API_KEY` = value from Part 3
4. **Deployments** tab → latest deployment → **⋯ → Retry deployment**.

✅ The URL now shows empty tiles and no error pill.

## Part 6: Google login for @boosters.kr only (20 min)

### 6a. Create the Cloudflare Zero Trust team
1. Cloudflare left menu **Zero Trust**.
2. Pick a team name, e.g. `boosters`. Your login domain becomes `boosters.cloudflareaccess.com`.
3. Choose the **Free** plan (50 users, $0; a card may be asked for verification).

### 6b. Create the Google OAuth client
1. Go to **console.cloud.google.com**, signed in with your @boosters.kr account.
2. Top bar **project picker → New project**, name `sales-pulse` → **Create**, then select it.
3. **APIs & Services → OAuth consent screen** (may be called **Google Auth Platform → Branding**):
   - App name `Sales Pulse`, support email = yours.
   - Audience/User type: **Internal**. This limits login to your Google Workspace. If "Internal" is greyed out, you're not on Workspace; choose External and rely on step 6d.
   - Save.
4. **APIs & Services → Credentials → Create credentials → OAuth client ID**:
   - Application type: **Web application**, name `Cloudflare Access`
   - Authorized JavaScript origins: `https://boosters.cloudflareaccess.com`
   - Authorized redirect URIs: `https://boosters.cloudflareaccess.com/cdn-cgi/access/callback`
   - Use *your* team name from 6a in both.
   - **Create**. Copy **Client ID** and **Client secret** and save as `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`.

### 6c. Connect Google to Cloudflare
1. **Zero Trust → Settings → Authentication → Login methods → Add new → Google Workspace** (or **Google** if not Workspace).
2. Paste the Client ID and Client secret. For Google Workspace, enter the domain `boosters.kr`.
3. **Save**, then click **Test**. A Google sign-in should succeed.

### 6d. Protect the site
1. **Zero Trust → Access → Applications → Add an application → Self-hosted**.
   - Application name `Sales Pulse`, session duration `1 week`.
   - Public hostname: `boosters-sales-pulse.pages.dev`, path empty.
   - Login methods: untick everything except **Google Workspace/Google**. Turn on **Instant Auth** so users skip the chooser.
2. **Policies → Add a policy**:
   - Name `Boosters staff`, Action **Allow**
   - Include → **Emails ending in** → `@boosters.kr`
   - Save the application.
3. Add a **second** application so the data senders aren't blocked:
   - Self-hosted, name `Sales Pulse ingest`, same hostname, path `api/ingest`.
   - Policy: Action **Bypass**, Include → **Everyone**. Save.
   - This path is still protected by `INGEST_TOKEN`.

✅ Open the URL in an incognito window. You're sent to Google. A @boosters.kr account gets in; a personal Gmail is refused.

## Part 7: Meta sync (10 min)

### 7a. Check the token
In Meta **Business Settings → Users → System users**, select your system user:
- **Assigned assets**: ad account `1298298124998350` with *View performance*.
- The token must include the **ads_read** permission.

Test it in a terminal (replace TOKEN):
```
curl "https://graph.facebook.com/v23.0/act_1298298124998350?fields=name&access_token=TOKEN"
```
✅ The reply contains `"name":"EQQUALBERRY_AMAZON_US"`.

### 7b. Add GitHub secrets
Repo → **Settings → Secrets and variables → Actions → New repository secret**:

| Name | Value |
|---|---|
| `META_TOKEN` | System User token |
| `INGEST_URL` | `https://boosters-sales-pulse.pages.dev/api/ingest` |
| `INGEST_TOKEN` | value from Part 2 |

### 7c. Run it
1. Repo → **Actions** tab. If asked, click **I understand… enable workflows**.
2. **Meta sync → Run workflow → Run workflow.**
3. After about 1 minute it should be green. Open the run: the last line reads `{"ok": true, "stored": N} N facts`.

✅ The dashboard shows Meta spend, CPM, and product filters. It now updates hourly by itself.

## Part 8: Amazon sync from AX (20 min)

Easiest route: open Claude Code on your desktop inside the `boosters_ax_portal` folder and paste the prompt at the bottom of this guide. It finds the tables and writes the query for you. Manual route:

1. SSH into the AX server (or any always-on machine that can reach the MySQL DB):
   ```
   git clone https://github.com/sungyyy26/daily-briefing.git
   cd daily-briefing
   pip3 install pymysql
   cp ax_sync/.env.example ax_sync/.env
   nano ax_sync/.env
   ```
2. Fill in `.env`:
   ```
   DB_HOST=...        DB_PORT=3306
   DB_USER=...        DB_PASSWORD=...     DB_NAME=...
   INGEST_URL=https://boosters-sales-pulse.pages.dev/api/ingest
   INGEST_TOKEN=...
   ```
   Use a **read-only** MySQL user.
3. In `ax_sync/push_amazon.py`, change the `QUERY` to your real tables. It must return one row per day per ASIN (US only) with columns `date, sku, sales, units, orders, sessions`.
4. In `ax_sync/product_map.json`, list every ASIN:
   ```json
   { "B0XXXXXXX1": "VIT/SRM", "B0XXXXXXX2": "VIT/CRM", "B0XXXXXXX3": "NAD/DUO" }
   ```
   LINE is VIT, NAD or BAK. FORM is SRM, CRM, DUO or TRIO.
5. Test: `python3 ax_sync/push_amazon.py` should print `{"ok": true, "stored": N}`.
6. Run it hourly: `crontab -e` and add this line:
   ```
   5 * * * * cd $HOME/daily-briefing && /usr/bin/python3 ax_sync/push_amazon.py >> $HOME/amazon_sync.log 2>&1
   ```

✅ The Total Sales, B.ROAS, CVR and CPA tiles fill in, and the status pill shows "Amazon · Xm ago".

## Part 9: Notion API (10 min, collect the token now)

1. Go to **notion.so/profile/integrations → New integration**:
   - Name `Sales Pulse`, workspace = Boosters, type **Internal** → **Save**.
   - **Capabilities**: tick **Read content** only.
   - Copy the **Internal Integration Secret** (`ntn_…`). Save as **NOTION_TOKEN**.
2. Open each Notion page or database the dashboard should read. Click **⋯ → Connections → Connect to → Sales Pulse**.
3. Copy each database's ID: open it as a full page. The URL looks like `notion.so/<workspace>/<32-char-id>?v=…`, and the 32 characters are the ID.
4. Add GitHub secret `NOTION_TOKEN` (same place as 7b).
5. Tell Claude which database(s) and what to show, e.g. "the launch calendar DB, show upcoming promos as markers on the trend chart". Claude then adds the Notion sync script.

## Part 10: Slack (15 min, collect the token now; alerts come later)

1. Go to **api.slack.com/apps → Create New App → From scratch**, name `Sales Pulse`, workspace = Boosters.
2. **OAuth & Permissions → Bot Token Scopes → Add**: `chat:write`, `channels:read`. Add `channels:history` only if the dashboard should read messages.
3. **Install to Workspace → Allow.** Copy the **Bot User OAuth Token** (`xoxb-…`). Save as **SLACK_BOT_TOKEN**. (A workspace admin may need to approve.)
4. In Slack, create a channel such as `#sales-alerts`. Type `/invite @Sales Pulse`.
5. Get the channel ID: open the channel → click its name → bottom of the **About** tab (`C0…`).
6. Add GitHub secrets `SLACK_BOT_TOKEN` and `SLACK_CHANNEL_ID`.
7. When ready, tell Claude your alert rules (e.g. "B.ROAS below 1.5 yesterday", "spend +30% day over day", "daily 9am summary").

## Part 11: Go live

1. Share `https://boosters-sales-pulse.pages.dev` with the team.
2. Tell Claude **"new site works"**. Claude deletes the old Claude-run sync job, which stops the Claude usage.
3. Optional: use a nicer address like `pulse.boosters.kr` via **Pages → Custom domains** (needs DNS access). Then update the Access application hostname to match.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| "Couldn't load data" | KV binding isn't named exactly `SALES`, or you didn't redeploy after Part 5 |
| Action or AX script returns **401** | `INGEST_TOKEN` differs between Cloudflare, GitHub and `.env` |
| Action returns **403** or HTML | Part 6d.3 bypass app for `api/ingest` is missing |
| Meta Action: "Unsupported version" | In `.github/workflows/meta-sync.yml` under `env:`, add `META_API_VERSION: "v24.0"` (or current) |
| Meta Action: "permission" error | System user lacks `ads_read` or the ad account asset |
| Google login: "redirect_uri_mismatch" | Team name in 6b.4 URIs doesn't match 6a |
| Personal Gmail can log in | Policy in 6d.2 isn't "Emails ending in @boosters.kr" |
| AI chat error | Check `ANTHROPIC_API_KEY` and billing credit |
| Amazon numbers missing | On AX server: `tail $HOME/amazon_sync.log` |

---

## Prompt for Claude Code on your desktop (Part 8)

Open Claude Code inside the `boosters_ax_portal` folder and paste:

> Read this repo to find how it connects to the Boosters MySQL DB and which tables hold Amazon US orders/sales, sessions (Business Report), and ASIN/SKU. Using the existing DB credentials, run **read-only** queries only (no INSERT/UPDATE/DELETE). Then, in `../daily-briefing`:
> 1. In `ax_sync/push_amazon.py`, set `QUERY` to return `date, sku (ASIN), sales, units, orders, sessions` per day per ASIN, US only, last 90 days.
> 2. Fill `ax_sync/product_map.json`, mapping each EQQUALBERRY ASIN to LINE/FORM (VIT=Vitamin Illuminating, NAD, BAK=Bakuchiol; SRM serum, CRM cream, DUO serum+cream, TRIO).
> 3. Create `ax_sync/.env` from the portal's DB config. Never commit it.
> 4. Do a dry run printing the first rows without sending. Show me the query and sample output before anything else.
