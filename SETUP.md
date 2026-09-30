# Sales Pulse setup (laptop, ~45 min)

**You need:** GitHub login (sungyyy26), your Meta System User token, an email for Cloudflare (free), a card for the Anthropic API (AI chat, pay-per-use), and SSH access to the AX server.

## 1. Merge the code into `main` (GitHub, 2 min)
1. Open github.com/sungyyy26/daily-briefing.
2. Click the yellow banner **Compare & pull request** for branch `ccr-1e9e3c88-ld36wi` (or **Pull requests → New → compare: ccr-1e9e3c88-ld36wi**).
3. **Create pull request → Merge pull request → Confirm.**

## 2. Make an ingest password (1 min)
This is a shared secret that lets GitHub and the AX server send data to your site.
- Mac terminal: `openssl rand -hex 32`, or use any password generator (40+ characters, letters and numbers).
- Save it in a notes app as **INGEST_TOKEN**. You'll paste it in 3 places.

## 3. Get an Anthropic API key for the AI chat (3 min)
1. Go to console.anthropic.com, sign up or log in.
2. **Settings → Billing**: add a card and a small credit (e.g. $10). Optional: set a monthly spend limit.
3. **API Keys → Create Key**, name it `sales-pulse`, copy it (starts with `sk-ant-`). Save as **ANTHROPIC_API_KEY**.

## 4. Create the Cloudflare Pages site (5 min)
1. Sign up at dash.cloudflare.com (free plan).
2. Left menu **Workers & Pages → Create → Pages → Import an existing Git repository**.
3. **Connect GitHub**, allow access to `sungyyy26/daily-briefing`, select it → **Begin setup**.
4. Settings:
   - Project name: `boosters-sales-pulse` (your URL becomes `https://boosters-sales-pulse.pages.dev`)
   - Production branch: `main`
   - Framework preset: **None**
   - Build command: *(leave empty)*
   - Build output directory: `public`
5. **Save and Deploy.** Wait for "Success".

## 5. Add storage and secrets to the site (5 min)
1. **Workers & Pages → KV** (sometimes under **Storage & Databases → KV**) **→ Create namespace**, name `sales-pulse`.
2. Open your Pages project → **Settings → Bindings → Add → KV namespace**:
   - Variable name: `SALES` (exactly), namespace: `sales-pulse` → Save.
3. **Settings → Variables and Secrets → Add** (type **Secret**, environment **Production**):
   - `INGEST_TOKEN` = your token from step 2
   - `ANTHROPIC_API_KEY` = key from step 3
4. **Deployments → latest → ⋯ → Retry deployment** (settings only apply after a redeploy).

## 6. Put a login in front of it (Cloudflare Access, 10 min)
1. Dashboard left menu **Zero Trust** (first time: pick a team name, choose the **Free** plan; it may ask for a card but charges $0 for up to 50 users).
2. **Access → Applications → Add an application → Self-hosted.**
   - Name: `Sales Pulse`, domain: `boosters-sales-pulse.pages.dev`, path empty.
   - Policy: name `Boosters staff`, action **Allow**, Include → **Emails ending in** → `@boosters.kr`.
   - Login method: **One-time PIN** (people get a code by email). Save.
3. Add a **second** application (so the data senders aren't blocked):
   - Self-hosted, same domain, path `api/ingest`.
   - Policy action **Bypass**, Include → **Everyone**. Save.
   - This path is still protected by INGEST_TOKEN.
4. Test: open `https://boosters-sales-pulse.pages.dev` in a private window. You should get a login screen, then the dashboard (no data yet).

## 7. Check the Meta token (2 min)
The System User needs the **ads_read** permission and the ad account `1298298124998350` assigned to it (Business Settings → Users → System users → Assign assets).
Quick check in a terminal (replace TOKEN):
```
curl "https://graph.facebook.com/v23.0/act_1298298124998350?fields=name&access_token=TOKEN"
```
It should return `"name": "EQQUALBERRY_AMAZON_US"`. If it says the version is invalid, use your current version and do step 8.4.

## 8. Turn on the Meta sync (GitHub Actions, 5 min)
1. Repo → **Settings → Secrets and variables → Actions → New repository secret**, add three:
   - `META_TOKEN` = System User token
   - `INGEST_URL` = `https://boosters-sales-pulse.pages.dev/api/ingest`
   - `INGEST_TOKEN` = token from step 2
2. Repo → **Actions** tab → enable workflows if asked → **Meta sync → Run workflow**.
3. After ~1 min it should be green, and the log ends with `{"ok": true, "stored": ...}`. Refresh the dashboard: Meta numbers appear.
4. (Only if step 7 needed another version) edit `.github/workflows/meta-sync.yml`, add `META_API_VERSION: "v24.0"` under `env:`.

It now runs every hour by itself.

## 9. Turn on the Amazon sync (AX server, 15 min)
SSH into the AX server, then:
```
git clone https://github.com/sungyyy26/daily-briefing.git
cd daily-briefing
pip3 install pymysql
cp ax_sync/.env.example ax_sync/.env
nano ax_sync/.env
```
Fill in:
- DB_HOST / DB_PORT / DB_USER / DB_PASSWORD / DB_NAME (a read-only MySQL user is best)
- `INGEST_URL=https://boosters-sales-pulse.pages.dev/api/ingest`
- `INGEST_TOKEN=` your token from step 2

Then:
1. `nano ax_sync/push_amazon.py`: change the SQL `QUERY` to your real table and column names. It must return `date, sku, sales, units, orders, sessions` per day per ASIN, US only.
2. `nano ax_sync/product_map.json`: list each ASIN, e.g.
   `{"B0ABC12345": "VIT/SRM", "B0DEF67890": "NAD/DUO"}`
3. Test: `python3 ax_sync/push_amazon.py` should print `{"ok": true, "stored": N}`.
4. Schedule hourly: `crontab -e` and add
   `5 * * * * cd $HOME/daily-briefing && /usr/bin/python3 ax_sync/push_amazon.py >> /tmp/amazon_sync.log 2>&1`

(The AX server must be allowed to reach `*.pages.dev` over HTTPS.)

## 10. Finish
- Share the URL with the team. Anyone with an @boosters.kr email can log in with an emailed code.
- Tell Claude "new site works" to delete the old Claude sync job, which stops the Claude usage.

**Troubleshooting**
- Dashboard says "Couldn't load data": KV binding not named `SALES`, or you didn't redeploy after step 5.
- Action or AX script gets 401: INGEST_TOKEN differs between places.
- Action gets 403 or a login page: the step 6.3 bypass for `api/ingest` is missing.
- AI chat error: check ANTHROPIC_API_KEY and billing credit.
