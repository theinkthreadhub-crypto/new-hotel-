# Setu — Database Crash / Data Loss Possibilities

**Setu — Restaurant & Hotel POS** · Powered by Aghanya Devanya Enterprises

Ye document batata hai ki Setu ka data kin-kin haalaton mein kho sakta hai, kharab ho sakta hai, ya "gayab" dikh sakta hai. Har point ke saath likha hai ki ye kab hota hai, kitna nuksaan hota hai, client kya kare, aur code mein kya fix chahiye.

---

## Setu ka data kahan rehta hai

| Jagah | Kya | Note |
|---|---|---|
| **localStorage** (key `hotelerp_v1`) | **Asli database.** Saare bills, menu, stock, kaccha tables, staff, settings, license | Software khulte waqt sirf yahi padha jata hai |
| **IndexedDB** (`AghanyaDevanyaERP_DB`) | Har save par poori copy (mirror) | **Software ise kabhi wapas padhta nahi.** Abhi ye sirf ek copy hai, recovery ka raasta nahi |
| **JSON Backup file** | Settings → Download Backup | Haath se lena padta hai. Asli recovery yahi hai |

- **EXE mode:** data `%LOCALAPPDATA%\AghanyaDevanyaERP\Data` mein, origin `http://127.0.0.1:8000`.
- **Browser mode:** data us browser ke profile mein, har address ka alag.

> **Sabse zaroori baat:** browser ka database **address (origin) ke hisaab se alag** hota hai. `127.0.0.1:8000`, `localhost:8000`, `127.0.0.1:5123` aur `file:///...` chaaron ka data **bilkul alag** hai.

---

## Saransh (Summary)

| # | Khatra | Kitna gambhir | Kitna sambhav | Status |
|---|---|---|---|---|
| 1 | Storage bhar jana (quota full) | 🔴 Bahut | 🔴 Pakka, 1–3 mahine mein | ✅ **Fixed** (Desktop/LAN) · Browser mode mein warning |
| 2 | Port badalne se data "gayab" (EXE) | 🔴 Bahut | 🟠 Kabhi-kabhi | ✅ **Fixed** |
| 3 | Data kharab hone par khaali data se overwrite | 🔴 Bahut | 🟢 Kam | ✅ **Fixed** |
| 4 | Do window/tab ek saath (Kitchen + Billing) | 🔴 Bahut | 🟠 Browser mode mein | ✅ **Fixed** (Desktop/LAN) · Browser mode mein abhi bhi |
| 5 | Galat / purana backup restore | 🟠 Medium | 🟠 Kabhi-kabhi | 🟡 Aadha (sirf Main Counter / Manager restore kar sakta hai) |
| 6 | Browser / Windows data clear | 🔴 Bahut | 🟠 Kabhi-kabhi | 🟡 Desktop mein roz auto-backup (60 din) |
| 7 | Alag address se kholna | 🟠 Medium | 🟠 Kabhi-kabhi | ✅ **Fixed** (Desktop/LAN: data address par nahi, file mein) |
| 8 | System date/time galat | 🟡 Kam | 🟠 Kabhi-kabhi | **Open** |
| 9 | Power cut / PC crash | 🟡 Kam | 🟠 Kabhi-kabhi | Theek hai |
| 10 | "Dal Tadka" menu par har start par data delete | 🔴 Bahut | Pakka tha | ✅ **Fixed** |
| 11 | IndexedDB store na banna | 🟡 Kam | Pakka tha | ✅ **Fixed** |

---

## Naya Update (8 Oct 2026) — LAN Server Mode

Setu Desktop App (EXE) ab ek **chhota server** chalata hai, aur database **browser mein nahi, file mein** (`%LOCALAPPDATA%\AghanyaDevanyaERP\Data\setu-db.json`) save hota hai. Isse:

- **#1 Storage:** 5 MB ki limit khatam. File GBs tak badh sakti hai.
- **#2 Port:** Port 8000 fixed hai. Setu pehle se khula ho to wahi khulta hai. Koi doosra program port le le to saaf error aata hai, random port nahi.
- **#3 Corrupt data:** Kharab file `setu-db.json.corrupt-<time>` naam se alag rakh di jaati hai, overwrite nahi hoti. Har save "atomic" hai (temp file → replace), power cut par aadhi file nahi banti.
- **Save fail hona (antivirus ne file pakdi):** Server 10 baar retry karta hai. Phir bhi fail ho to version aage nahi badhta, device dobara bhejta hai, aur error `Data\setu-server.log` mein likha jata hai. Footer mein laal "connection toota" dikhe to ye log file vendor ko bhejein.
- **Do server ek port par:** Windows par ab mumkin nahi (port share band).
- **#4 Do window / phone / tablet:** Har device apna badlaav version ke saath bhejta hai. Takraav hone par record-by-record merge hota hai. Duplicate bill/KOT number apne aap naye ho jaate hain.
- **#6 Backup:** `Data\Backups\setu-YYYY-MM-DD.json` roz apne aap banta hai (60 din tak). Phir bhi PC ke bahar backup zaroor rakhein.
- **#7 Address:** Data file mein hai, isliye `localhost` / `127.0.0.1` / phone ka IP, sab ek hi data dekhte hain.

**Browser mode** (`hotel_erp.html` seedha browser mein, ya test link) mein purane khatre (#1, #4) abhi bhi hain. Wahan 80% storage bharte hi warning aati hai. Asli restaurant mein hamesha **Desktop App** chalayein.

---

## 1. Storage bhar jana (localStorage quota full) 🔴

**Kya hota hai:** Chrome/Edge/WebView2 mein localStorage ki limit lagbhag **5 MB (~50 lakh characters)** hai. Setu saara data isi ek jagah rakhta hai aur purane bills kabhi hatata nahi.

**Hisaab:**
- Ek normal bill (4 items) ≈ **660 characters**.
- 150 bills/din ≈ 1 lakh characters/din.
- Iske alawa menu, stock, Zomato/Swiggy orders (kabhi delete nahi hote), expenses aur KOT (7 din) bhi jagah lete hain.
- **Lagbhag 40–50 din mein storage full.** Kam bills wale hotel mein kuch mahine.

**Full hone par:**
- Har save par error popup aata hai: *"Data save nahi hua: QuotaExceededError"*.
- Naye bills screen par dikhte hain lekin **save nahi hote**. Software band karte hi wo bills **gayab**.
- Mirror IndexedDB mein chala jata hai, lekin software use padhta nahi, isliye wahan se bhi wapas nahi aata.
- Billing practically band ho jaati hai.

**Client kya kare (abhi):** Roz Backup lein. Popup aate hi turant Backup download karein aur vendor ko call karein.

**Code fix (zaroori):**
- Main database ko **IndexedDB** par le jaayein (limit GBs mein hoti hai). localStorage sirf chhoti settings ke liye rahe.
- Ya: 90 din se purane bills ko "Archive" file mein nikaal kar localStorage se hatayein.
- Storage 80% bharne par pehle se warning dikhayein.

---

## 2. Port badalne se data "gayab" dikhna (EXE mode) 🔴

**Kya hota hai:** `app_main.py` pehle port **8000** try karta hai. Agar 8000 par pehle se kuch chal raha ho (doosra software, ya **Setu ki doosri copy** jo galti se do baar khul gayi), to wo **random port** (jaise 52341) le leta hai.

**Asar:**
- Naya port = naya address = **khaali database**.
- Setu "New Restaurant Sign Up" dikhata hai, jaise pehli baar install hua ho. Owner ghabra jata hai ki data ud gaya.
- Agar staff ne usi mein billing kar di, to wo bills us random port wale database mein jaate hain. Agli baar port alag hoga, to **wo bills kabhi wapas nahi dikhenge**.
- Purana data port 8000 wale database mein safe hai. Agli baar 8000 free milte hi wapas dikhega.

**Client kya kare:** Sign Up screen achanak aaye to **Sign Up na karein.** Setu band karein, PC restart karein, phir kholein.

**Code fix (zaroori):**
- Port fixed rakhein. 8000 busy ho to check karein ki kahin Setu khud to nahi chal raha (single-instance). Agar haan, to wahi window aage laayein. Doosra program ho to saaf error dikhayein, random port na lein.

---

## 3. Data kharab hone par khaali data se overwrite 🔴

**Kya hota hai:**
1. Software khulte waqt `load()` localStorage padhta hai.
2. Agar data kharab (corrupt JSON) mila, ya usme `settings` nahi hai, to wo chupchap **khaali naya database** (`seed()`) bana leta hai.
3. Turant `save()` chalta hai, jo **purane (repair ho sakne wale) data ke upar khaali data likh deta hai.** Usi waqt IndexedDB mirror bhi khaali ho jata hai.

**Kab ho sakta hai:** Disk error, antivirus ka file chhedna, ya save ke beech mein PC band hona (bahut kam).

**Asar:** Saara data ek jhatke mein khatam. Backup ke alawa koi raasta nahi.

**Code fix:**
- Corrupt data mile to use `hotelerp_v1_corrupt_<date>` naam se alag rakhein, overwrite na karein.
- IndexedDB mirror se recovery ki koshish karein.
- User ko saaf message dein: "Data padha nahi ja saka, Backup restore karein".

---

## 4. Do window / tab ek saath khulna 🔴

**Kya hota hai:** Har window apne paas poore data ki copy (memory mein) rakhti hai, aur save karte waqt **poora database apni copy se overwrite** karti hai. Jo aakhri save karega, wahi bachega.

**Asli udaharan:**
1. Browser mode mein ek tab mein Billing, doosre tab mein Kitchen Display (Full Screen) khula hai.
2. Billing tab mein 10 bills bane.
3. Kitchen tab ne "Food Ready" dabaya, jisse **uski purani copy save ho gayi.** Usme wo 10 bills the hi nahi.
4. **10 bills gayab.** Bill number bhi dobara repeat ho sakte hain.

> Kitchen Display har 15 second mein sirf KOT list refresh karta hai, bills nahi. Isliye ye khatra **Kitchen Display feature ke saath badh gaya hai.**

- **EXE mode:** ek hi window hoti hai, isliye EXE mein ye khatra nahi hai.
- **Browser mode:** do tab kholna aasaan hai.

**Client kya kare:** Setu ek hi window/tab mein chalayein. Kitchen Mode usi window mein kholein aur Billing ke liye Esc se wapas aayein.

**Code fix (zaroori):**
- Browser ka `storage` event sunein. Doosri window save kare to turant naya data load karein.
- Save se theek pehle latest data padh kar sirf apna badlaav jodein (merge).
- Ya ek waqt mein sirf ek "active" window allow karein, aur doosri window par "Setu kahin aur khula hai" dikhayein.

---

## 5. Galat ya purana backup restore karna 🟠

**Kya hota hai:** Restore poore database ko backup file se **replace** kar deta hai. Check sirf itna hota hai ki file mein `settings` aur `bills` hain.

**Khatre:**
- **Purana backup:** us din ke baad ke saare bills, stock aur staff entries chali jaati hain. Koi chetavani nahi ki "ye backup 20 din purana hai".
- **Adhuri/purani file:** `menu`, `stock` ya `txns` na ho to software khulte hi screens crash ho sakti hain (khaali/white screen).
- **Doosre hotel ka backup:** uska login, password aur **license** bhi aa jata hai. License ki din-ginti bhi backup ke saath badal jaati hai.

**Code fix:**
- Restore se pehle dikhayein: backup ki date, kitne bills, kaunsa hotel. Phir confirm karein.
- Restore se pehle current data ka auto-backup lein.
- Saare zaroori arrays (`menu`, `stock`, `txns`, `cash`, `seq`…) ki default value bharein.
- License ko backup se restore na hone dein.

---

## 6. Browser / Windows data clear hona 🔴

**Kab:**
- Browser mode mein "Clear browsing data → Cookies and site data".
- CCleaner jaise cleaner software.
- Windows reset, ya naya user account.
- EXE mode mein `%LOCALAPPDATA%\AghanyaDevanyaERP` folder delete hona.

**Asar:** Poora data khatam. Software dobara Sign Up maangega.

**Bachav:** Sirf **roz ka JSON Backup**. Backup PC ke bahar rakhein (pen-drive, Google Drive, WhatsApp par khud ko bhejein).

**Code fix (suggest):** Din band karte waqt (Day Report) apne aap backup download ho, ya "Aaj backup nahi liya" ki yaad dilaayein.

---

## 7. Alag address se kholna 🟠

Ye sab **alag database** hain:

| Kaise khola | Address |
|---|---|
| EXE | `http://127.0.0.1:8000` |
| `Start-ERP-Server.bat` / Launcher | `http://localhost:8000` |
| `hotel_erp.html` par double-click | `file:///...` |

**Asar:** Staff kabhi EXE se, kabhi browser se kholta hai, to dono jagah alag-alag bills bante hain. Hisaab nahi milta aur lagta hai data gayab hai.

**Fix:** Client ko sirf ek tareeka dein (EXE). Launcher aur `.bat` ko bhi `127.0.0.1:8000` par kar dein.

---

## 8. System date/time galat 🟡

**Asar:**
- Bills galat date mein chale jaate hain, isliye Day Book aur Report galat ho jaati hai.
- Date peeche karne se license ke din badh jaate hain, aur aage karne se license jaldi expire.
- Crash nahi hota, lekin hisaab bigadta hai.

**Fix:** Pichhle save ki date yaad rakhein. Agar system date usse peeche ho to warning dikhayein.

---

## 9. Power cut / PC crash 🟡

- Save turant hota hai (har bill par). Power cut se zyada se zyada **aakhri kuch second** ka kaam jaa sakta hai.
- "Save Kaccha Bill" daba chuke tables safe rehti hain. Jo cart abhi tak save nahi hua (sirf screen par hai), wo chala jayega.
- Bahut kam case mein save ke beech power jaane se data corrupt ho sakta hai, jiske baad point 3 wala khatra aata hai.

**Bachav:** UPS lagayein, roz Backup lein.

---

## 10. ✅ FIXED — "Dal Tadka" wala data delete

**Tha:** Software har start par menu mein "Dal Tadka", "Veg Thali", "Paneer Butter Masala" ya stock mein "Paneer" dekh kar use demo data samajhta tha, aur **saare bills, menu, stock aur kaccha tables delete** kar deta tha. Har us restaurant ke saath, jiska asli menu aisa tha.

**Ab:** Ye safai sirf ek baar chalti hai, aur sirf tab jab hotel ka naam purane demo wala ("The Grand Annapurna Restaurant") ho. Restore kiye gaye backup par kabhi nahi chalti. Fix commit: `cb1a2e2`.

## 11. ✅ FIXED — IndexedDB store na banna

**Tha:** Pehli baar kholne par mirror database ka store banta hi nahi tha. Har save par background error aata tha aur mirror kabhi save nahi hota tha.

**Ab:** Version 2 ke saath store hamesha banta hai. Fix commit: `cb1a2e2`. (Phir bhi mirror se recovery ka raasta abhi nahi hai, dekhein point 1 aur 3.)

---

## Fix karne ki Priority

| Order | Kaam | Kyun pehle |
|---|---|---|
| 1 | ~~Main database file par shift + storage warning~~ ✅ Ho gaya | — |
| 2 | ~~Fixed port + single instance (EXE)~~ ✅ Ho gaya | — |
| 3 | ~~Do window / device ka merge~~ ✅ Ho gaya | — |
| 4 | ~~Corrupt data par overwrite band~~ ✅ Ho gaya | — |
| 5 | Restore se pehle preview + auto-backup + license protect | Galat restore se nuksaan |
| 6 | ~~Roz auto-backup~~ ✅ Desktop mein ho gaya · PC ke bahar copy abhi bhi haath se | — |

## Client ke liye 5 Niyam (abhi se)

1. **Roz din band karte waqt Backup lein** (Settings → Download JSON Backup) aur PC ke bahar rakhein.
2. Setu **sirf EXE se** aur **ek hi window** mein chalayein.
3. Achanak **Sign Up screen** aaye to Sign Up na karein. Band karke dobara kholein, aur vendor ko batayein.
4. **"Data save nahi hua"** popup aaye to turant Backup lein aur vendor ko call karein.
5. PC ki **date/time sahi** rakhein, aur cleaner software se Setu ka folder/browser data saaf na karein.
