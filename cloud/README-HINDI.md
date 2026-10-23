# Setu Pro Cloud SaaS — Setup Guide (Hindi)

*Powered by Aghanya Devanya Enterprises*

Ek hi Cloudflare deploy par **saare hotel**. Har hotel:

- khud online **Sign Up** karta hai → **Hotel Code** (jaise `SHARM482`) + free trial (default 14 din)
- phone / tablet / laptop browser se **Hotel Code + PIN** se login karta hai
- chahe to counter PC par **Setu Desktop App (EXE)** lagata hai: internet jaane par bhi billing + seedha thermal print chalta hai, net aate hi cloud se sync
- **Razorpay** se monthly / yearly **auto-renew** subscription leta hai

Har payment par Worker ek asli **signed SETU license key** (wahi ECDSA system jo `keygen.py` banata hai) hotel ke data mein daal deta hai.
App use apne aap activate kar leta hai — cloud aur counter PC dono ka license badh jata hai. Payment band = trial/plan + 3 din ke baad
cloud par save band (data padhna aur backup chalta rehta hai).

## 1. Ek baar ka setup (vendor)

Cloudflare ka free account aur PC par Node.js chahiye.

```bash
cd cloud
npm install
npx wrangler login
```

### Secrets

License signing key (wahi `setu-license-private.pem` jo `keygen.py` use karta hai — screen par print nahi hoti):

```bash
npm run license-key -- "C:\Users\jjcka\Desktop\claude cowork\Hotel Software\setu-license-private.pem"
```

Vendor Admin Panel ki key (`npm run new-key` se lambi random key banayein, phir paste karein):

```bash
npm run secret ADMIN_KEY
```

Razorpay (Dashboard → Account & Settings → API Keys; pehle **Test Mode** mein try karein):

```bash
npm run secret RAZORPAY_KEY_ID
```

```bash
npm run secret RAZORPAY_KEY_SECRET
```

```bash
npm run secret RAZORPAY_WEBHOOK_SECRET
```

### Plans (Basic / Premium / Diamond)

1. Razorpay Dashboard → **Subscriptions → Plans** → har plan ke liye monthly aur yearly plan banayein (kul 6).
2. Unke `plan_...` ID [wrangler.toml](wrangler.toml) ki `PLANS` mein daalein. Price, din aur naam wahin badlein.
3. Kis plan mein kaunse module hain: `src/worker.js` mein `TIERS`. Free trial: `TRIAL_DAYS`, `TRIAL_TIER`.

### Domains (optional)

- **Subdomain** (`royal.setupro.in`): aapka domain Cloudflare par ho → `BASE_DOMAIN`, `APP_HOST` set karein aur `routes` wali line kholein.
- **Hotel ka apna domain** (`erp.hotelroyal.com`): Cloudflare for SaaS chalu karein → `SAAS_CNAME_TARGET` var + secrets `CF_API_TOKEN`, `CF_ZONE_ID`.
  Super Admin se domain jodne par DNS records dikhte hain; hotel unhe apne domain provider mein daalta hai; verify + HTTPS hone par hi chalu.

### Deploy

```bash
npm run deploy
```

Ye `https://setu-cloud.<aapka-naam>.workers.dev` jaisa link dega.

### Razorpay Webhook

Razorpay Dashboard → **Webhooks → Add**:

- URL: `https://setu-cloud.<aapka-naam>.workers.dev/api/razorpay/webhook`
- Secret: wahi jo `RAZORPAY_WEBHOOK_SECRET` mein daala
- Events: `subscription.charged`, `subscription.activated`, `subscription.halted`, `subscription.cancelled`, `subscription.completed`

## 2. Hotel ka flow

1. Hotel owner link kholta hai → **Free Sign Up karein** → Hotel Code + Counter PC Sync Key milti hai.
2. Settings (G) mein Cashier / staff PIN banata hai (cloud par 1234 / 1111 nahi chalte).
3. Staff: link + Hotel Code + apna PIN.
4. Trial khatam hone se pehle: Settings (G) → **Setu Cloud** card → Monthly / Yearly → Razorpay (UPI / card, auto-renew).
5. Counter PC (optional): Setu Desktop App → Settings (G) → **Setu Cloud Sync** → Cloud URL + Hotel Code + Sync Key.
   Sync Key kho jaye to cloud par Manager login karke **Counter PC Sync Key** dabakar nayi banayein.

## 3. Super Admin Panel

`https://setu-cloud.<aapka-naam>.workers.dev/admin.html` → `ADMIN_KEY` daalein.

| Hissa | Kya karta hai |
|---|---|
| Dashboard | Total / paid / trial / expired hotel, 30 din ka payment, MRR andaaza, jald khatam hone wale |
| Hotels | Search, status, plan, domain; click karke hotel kholein |
| + Naya Hotel | Business type template + plan + din + owner password → Hotel Code. Owner pehli baar usi password se login karta hai |
| Overview & Subscription | Profile, + din (cash / UPI), suspend, lifetime, payment list |
| Plan & Features | Plan badlein, template lagayein, har module ON / OFF / plan ke hisaab se |
| Billing Builder | Paper 58 / 80 / A6, logo, table / customer line, header, footer, custom fields (jaise Vehicle No), live preview |
| Rules | Cashier max discount %, bade bill par mobile zaroori |
| Domains | Subdomain ya hotel ka apna domain, DNS records, status check |
| Support | 30 min – 2 ghante ka **sirf-dekhne** wala link; hotel ko Settings mein dikhta hai |
| Audit Log | Super Admin ka har badlav |

Super Admin ka har badlav database mein save hota hai aur hotel ke saare devices par kuch second mein lag jata hai — **redeploy nahi karna padta**.
Band module ka data server bhi save nahi karta. Naya module banana ho tabhi code + deploy chahiye.

## Kya kahan hai

| Cheez | Kahan |
|---|---|
| Hotel ka data | Uska apna Durable Object (SQLite), roz ka backup 30 din |
| Hotel list | `SetuRegistry` Durable Object |
| Login | Hotel Code + PIN, 5 galat = 15 min lock, 180 din yaad |
| Payment | Razorpay Subscription → webhook → signed license key; plan ke tier par hotel apne aap shift |
| Config | `D.saas` (plan, modules, bill template, rules) — server likhta hai, device sirf padhta hai |
| Counter PC | Asli offline copy, har 5 sec sync, seedha print |

## Local test

```bash
cp .dev.vars.example .dev.vars
npm run dev
```

`.dev.vars` mein test keys daalein. Ye file git mein nahi jaati — test ke baad delete kar dein, kyunki usme private key hoti hai.
