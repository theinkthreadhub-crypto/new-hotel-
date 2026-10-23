# AGENTS.md — Setu (Restaurant & Hotel POS)

Guide for AI coding agents (Claude Code, Codex, Cursor, etc.) working in this repo.

## What this is

**Setu** is an offline restaurant/hotel billing POS, *Powered by Aghanya Devanya Enterprises*.
It runs as a single HTML page, either in Chrome/Edge or inside a Windows desktop
wrapper (`.exe` built with PyInstaller + pywebview). There is no backend and no
internet dependency at runtime. All data lives on the customer's PC.

- Users: Indian restaurant owners, cashiers and kitchen staff.
- UI language: Hinglish (Roman Hindi + English), e.g. "Bill save ho gaya".
- Branding rule: the product name is **Setu**. Keep every
  "Powered by Aghanya Devanya Enterprises" line and the licensing authority
  name exactly as they are.

## Files

| File | Purpose |
|---|---|
| `hotel_erp.html` | The entire app: CSS, HTML shell and all JavaScript (~5.7k lines). Almost all work happens here. |
| `app_main.py` | Main-counter launcher + LAN server on fixed port 8000 (`0.0.0.0`). Keeps the shared database in `setu-db.json` with daily `Backups/`, serves phones/tablets, opens the pywebview window. `--server` = no window. Data dir: `%LOCALAPPDATA%\AghanyaDevanyaERP\Data`. |
| `Aghanya-Devanya-Hotel-ERP.spec`, `Build-New-EXE.bat` | PyInstaller build. The `.bat` passes its own flags and does not use the `.spec`. Keep both in sync if you add bundled files. `.github/workflows/build-exe.yml` builds the same EXE on GitHub (Actions artifact `Setu-POS-Setup`) and must use the same flags. |
| `cloud/` | **Setu Pro Cloud SaaS** (Cloudflare Worker). `SetuHotel` Durable Object (SQLite) per hotel, keyed by Hotel Code (`X-Setu-Hotel`) or by the hotel's own domain/subdomain (registry `domain` table; host beats header). `SetuRegistry` = hotels, domains, payments, Super Admin audit. Catalogue in `worker.js`: `FEATURES` (module -> data keys), `TIERS` (basic/premium/diamond), `TEMPLATES` (restaurant/cafe/hotel/cloudkitchen). Per-hotel `config` (tier, feature overrides, billing template, rules) is written into the data as `D.saas` by `prepare()` on every save; clients only read it. Off modules: server keeps its stored copy of their keys. Razorpay plans in `PLANS` var (`tier_cycle`). Super Admin UI: `static/admin.html` (`/api/admin/*`, `ADMIN_KEY`). See `cloud/README-HINDI.md`. |
| `manifest.json`, `sw.js` | PWA install + offline cache. |
| `keygen.py`, `Generate-Activation-Keys.bat` | Vendor-only license key signer (ECDSA P-256). Needs `setu-license-private.pem`, which is **never** in git (`*.pem` ignored). `python keygen.py <INSTALL-ID> <plan>`. |
| `favicon.ico`, `icon-*.png`, `logo.png` | Branding assets. |

Not in git (see `.gitignore`): `build/`, `dist/`, `*.exe`, `*.bak`,
`Activation_Keys/`, `Activation-Keys-*.txt`, `*.pem`. **Never commit the private signing key,
generated activation keys or EXE binaries.**

## Run and check

```bash
python app_main.py --server --port 8000 --data ./test-data
```
Then open `http://127.0.0.1:8000/hotel_erp.html` (main counter) and `http://<LAN-IP>:8000/hotel_erp.html`
(acts as a phone: asks for the Manager/Cashier PIN). `python -m http.server` still works and runs the
app in **browser mode** (localStorage, no LAN). Use **"1-Click Demo Login"** (demo / demo)
and the test license key `AD-DEMO-24HR-TEST`.

There is no build step and no test suite. Before committing:

1. Syntax-check the main script. Extract the last `<script>` block and run `node --check` on it.
2. Exercise the changed flow in a browser and watch the console for errors.
3. `sw.js` serves cache-first. After changing `hotel_erp.html`, bump `CACHE_NAME` in `sw.js`.
   When testing, unregister the service worker and clear caches, otherwise you will test a stale file.

Rebuild the EXE on Windows with `Build-New-EXE.bat`.

## Architecture of `hotel_erp.html`

- **Two `<script>` blocks.** The first is the vendored MIT `qrcode-generator` 1.4.4
  (used by `qrSvg()`). Do not edit it. The second is the app.
- **State:** one global object `D`. Always call `save()` after mutating `D`. Two storage modes:
  - **LAN / desktop mode** (`SRV.on`, page served by `app_main.py`): `save()` debounces `srvPush()`, which POSTs
    the whole `D` with `baseVersion`. On HTTP 409 the client runs `merge3(base, mine, theirs)` (record-level
    3-way merge by `id`, key-level for maps, `seq` takes the max, duplicate new bill/KOT numbers are renumbered)
    and retries. `srvPoll()` checks `/api/version` every 2.5 s and reloads `D`; `srvRefreshScreen()` re-renders
    live screens. Never write code that assumes `D` is only changed by this device.
  - **Browser mode** (no `/api/ping`): `load()` / `save()` use `localStorage['hotelerp_v1']` + an IndexedDB mirror.
- **LAN auth:** requests from 127.0.0.1 are trusted. Other devices call `/api/login` with the Manager or Cashier
  PIN and send `X-Setu-Token`. First upload and forced restore/reset (`SRV.forceNext`) are main-counter / admin only.
- **Schema migration:** `seed()` defines a fresh install. `ensureGrowth(s)` back-fills
  newer fields (settings defaults in `GROWTH_DEFAULTS`, `kots`, `staff`, `att`, `outlets`, `reservations`, `seq.token`).
  When you add a field, give it a default in **both** places. `load()`, `restore()` and
  `resetAll()` all pass through `ensureGrowth`.
- **Navigation:** `MENU` holds the rows `[hotkey, label, screenKey, sidebarCategory]`.
  `SCREENS` maps each screenKey to a render function. `go(key)` checks auth and license, then renders
  into `#main`. Screens are plain functions that set `main.innerHTML` from template strings.
  A new screen needs a `MENU` row, a `SCREENS` entry and a `scrXxx()` function.
  Hotkeys must be unique. Letters already used: B Z L P E I D C W S M T Q R A O N H X F U Y V K G. Free: J.
- **UI helpers:** `modal(title, html)`, `closeModal()`, `tryCloseModal()`, `toast(msg)`,
  `waOpen(phone, text)`, `waOwner(text)`, `printDoc([htmlParts])`.
  Money is formatted with `money()` / `rs()` and rounded with `r2()`. Dates are `YYYY-MM-DD` strings from `today()`.
- **Escaping:** wrap every user-entered value with `esc()` before it goes into HTML.
  In inline `onclick` handlers pass ids, never names or free text.

### Key domain flows

- **Billing:** the cart lives in the global `B` (`newB()`). Channels are `Dine-In`, `Takeaway`, `Zomato` and `Swiggy`.
  - **Dine-In:** a running "Kaccha Bill" is stored per table in `D.kaccha[table]`.
  - **Final bill:** `finalizePakkaBill()` turns the cart into a tax invoice in `D.bills` and frees the table.
  - **Totals:** `calc(items, discount, gstRate)` computes every total. Do not compute totals by hand.
- **Kitchen Display (KOT):** `pushKot()` adds tickets to `D.kots`.
  - **Delta only:** `B.sent` / `kaccha.sent` record what the kitchen already has, and `cartDelta()` sends only new quantities.
  - **Example:** 3 roti, then 5 more, gives a KOT for 3, a KOT for 5, and one bill line of 8.
  - **Keep this invariant** when you change billing.
- **Loyalty:** points are derived from bills (`ptsEarned` / `ptsUsed`) and are never stored separately.
  `ptsBal()` / `ptsBalAt()` sum them. Zomato/Swiggy bills never earn points.
  Loyalty discount is part of `bill.disc` and is also kept in `bill.loyaltyDisc` for display.
- **Customers** are derived from bills that carry a 10-digit phone number (`customers()`).
- **Stock:** each menu item `recipe` holds `[{sid, qty}]`. `applyStock(bill.used, ±1)` runs on bill save and on bill cancel.
- **Money that is not income/expense:** `NON_INCOME_HEADS` (wallet top-ups, Zomato/Swiggy settlements) and
  `NON_EXPENSE_HEADS` (supplier payments) move cash but are excluded from margin in `summary()`, so sales/purchases are not counted twice.
- **Wallet:** balance = top-up receipts (`txn.phone`) − bills with `mode: 'Wallet'` (`walletBal()`).
- **Tokens:** `nextToken()` restarts daily (`seq.tokenDate`); only Takeaway bills / parcel QR orders get one when `settings.tokenOn`.
- **Captain app:** `captainSend()` merges the waiter's items into the table's kaccha bill via `kacchaToB()` + `saveKacchaBill(true, true)`.
- **Setu Cloud:** `CloudSync` in `app_main.py` keeps the counter PC as master and syncs `setu-db.json` with the hotel on the Worker
  (`setu-cloud.json` = URL + Hotel Code + sync key, `setu-cloud-base.json` = last common copy). It uses a Python port of `merge3`
  with the cloud as "mine", so bills printed at the counter keep their numbers. **If you change `merge3` / `mergeNode` in the HTML,
  change the Python port too.** On the cloud (`SRV.cloud` / `SRV.saas`) login = Hotel Code + PIN (or the hotel's domain), weak PINs
  are refused, 5 wrong PINs lock an IP for 15 min, direct printing is off. Never trust the client for billing or modules: the Worker
  decides `blocked`, `D.saas` and what off-modules may change.
- **Setu Pro config in the app:** `featureOn()` / `screenOn()` hide modules (`FEATURE_SCREENS`, `drawSide`, `go`). `applySaas()` (in
  `ensureGrowth`) maps the bill template and rules onto `settings`. `billFields()` = custom bill fields (`B.extra` -> `bill.extra`,
  printed by `billHTML` / `escBill`). `saasRules().phoneAbove` needs a mobile on big bills. Support links (`#support=CODE.TOKEN`) open a
  read-only session (`SRV.readOnly`). LAN / browser installs have no `D.saas`, so everything stays on.
- **Dashboard setup:** the owner/manager picks what the Gateway shows (`dashSetup()`): sections in `DASH_PARTS` hidden via
  `settings.dashHide`, launchpad tiles via `settings.dashTiles` (missing = all). New Gateway sections need a `DASH_PARTS` entry + `on('key')` wrap.
- **Multi-outlet:** no shared cloud across outlets yet. Each outlet exports `outletSnapshot()` as JSON (daily totals only, no customer data), and the owner imports the files.
- **License:** keys are `SETU-...` strings = 13-byte payload (kind, days/minutes, install-ID hash, serial,
  issue day) + 64-byte ECDSA signature, base32. `getActivationKeyInfo()` verifies with WebCrypto against
  `LIC_PUBKEY` and `settings.installId` (needs a secure context: 127.0.0.1 / localhost / https).
  Used keys go to `subscription.usedKeys`. `subscription.lastSeen` blocks clock rollback.
  Built-in `AD-DEMO-*` keys work once per install and never shorten a running license.
  Never put real keys, salts or private keys in the page.
- **Staff & permissions:** `activeUser = {name, role: 'admin'|'cashier', access: 'manager'|'cashier'|'captain'}`.
  Staff log in with their own PIN (`staff[].pin/access`). `go()` blocks `CASHIER_BLOCK` screens and keeps
  captains on `CAPTAIN_ALLOW`. Sensitive actions call `withManager(label, fn)` (manager PIN modal) and
  `audit(action, detail, amount, ref, approvedBy)`. `AUDIT_ALERTS` feed the Audit screen (V), dashboard and daily report.
  Keep both when you add a new way to remove money or food from the books.
- **GST type:** `gstRate()` (0 for composition / unregistered) — never read `settings.gst` directly for totals.
  Bills store `scheme`; `billTitle()` prints TAX INVOICE / BILL OF SUPPLY / BILL. FSSAI number prints in `head()`.
- **Printing:** `directPrint()` (desktop server + `printMode: 'direct'`) builds ESC/POS with `EscPos` and POSTs
  `/api/print` (RAW job via winspool, no dialog). KOT items are split by `catPrinters[category]` in `directKot()`.
  Otherwise `printDoc()` uses the browser dialog. Thermal receipts are ASCII only (`asciiSafe`).
- **License:** `activateLicenseKey()` / `getSubscriptionInfo()` / `checkExpiryLock()`.
  Changes here affect revenue. Do not loosen checks, add bypasses or print key lists unless the owner explicitly asks.

## Gotchas (learned the hard way)

- **Data wipe on load.** `load()` used to treat any menu containing "Dal Tadka" or "Paneer" as demo data
  and wiped real bills on every launch. It now runs once (`demoCleanupDone`) and only for the old
  demo hotel name. Never add heuristics that delete user data.
- **IndexedDB.** Open it only through `openIDB()` (version 2, which creates the store). Bump the version
  if you add stores.
- **Downloads.** `backup()`, `menu.html`, CSV and outlet exports use blob links. They work in the
  browser and in the EXE, but not inside sandboxed preview iframes.
- **Line endings.** The repo uses LF. Keep LF when you write files.
- **Service worker** must never cache `/api/*` (see `sw.js`).
- **Port is fixed** on purpose. A random port used to change the browser origin and made data look lost.
- **Corrupt data** is copied aside (`setu-db.json.corrupt-*`, `hotelerp_v1_corrupt_*`), never overwritten.
- **Server writes:** `SetuStore.write()` updates version/memory only after `os.replace` succeeds (retries on
  Windows locks). Failures go to `setu-server.log`. Keep that order or a restart loses data.
- **Async license:** activation functions are `async` (WebCrypto). Await them.
- **Paper sizes.** Keep `paper()` and `printDoc()` working for both A6 and 58/80 mm thermal printing.

## Conventions

- Match the surrounding style: 2-space indent, `const` arrow helpers, template-string HTML, semicolons.
- No frameworks, bundlers or CDNs for JavaScript. Everything must work offline.
  Google Fonts is the only external request, and it is optional.
- Keep every feature usable by keyboard (Enter to add, Esc to go back, hotkeys).
- Write UI copy in short Hinglish. Use no emojis in the app UI or in printed bills.
- Branch: `hotel-software`. Leave `main` alone unless asked.
- Commit messages: an imperative summary line, then a body that explains why.
