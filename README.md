# Dalil

**A WhatsApp medicine companion for older patients in Lebanon, and for the family that looks after them from far away.**

Built solo by Julien Haber for the World Bank x Hack-Nation "Small AI for Development" challenge, Health track (Oct 3 to 4, 2026).

**Try it without WhatsApp:** the [click-through demo](https://julienelhaber.github.io/dalil/) replays Dalil's real messages, in Arabic and English. **Video (about 3 minutes):** [watch it](https://drive.google.com/file/d/1r6pgOUHpd4GG1Mnr4ZK-UWUfymNsOoWF/view?usp=sharing).

## The problem

Because of Dalil, an older patient in Lebanon who takes several medicines will confirm or flag each dose on WhatsApp when it is due, and will be warned before taking a second brand of a medicine he already takes, which he would otherwise miss or double without anyone noticing; we know because more than 11% of Lebanon's population is over 65, the highest share in the Arab region, medicines became scarce and expensive after the 2019 crisis, patients now ration or substitute medicines to save money, and 195,433 Lebanese emigrated between 2018 and 2021.

- **Older and sicker:** more than 11% of Lebanon's population is over 65, the highest share in the Arab region, and the Ministry of Public Health estimates that about 45% of older people have at least one chronic disease, mainly respiratory, cardiovascular and diabetes ([National Strategy for Older Persons in Lebanon 2020-2030](https://www.unescwa.org/sites/default/files/news/docs/online_-_final_english_strategy_for_online_use_1.pdf), Ministry of Social Affairs).
- **Scarce and expensive medicines:** Lebanon imports about 95% of its medicines. After subsidies on chronic disease medicines were removed, diabetes medicines cost 21% of the mean monthly income in 2023, with great shortages, insulin among them ([Chehayeb et al., PLOS Global Public Health, 2023](https://journals.plos.org/globalpublichealth/article?id=10.1371/journal.pgph.0002538)).
- **Rationing and substituting:** patients are "rationing or substituting medicine to save money, with serious adverse health impacts" ([Amnesty International, February 2023](https://www.amnesty.org/en/latest/news/2023/02/lebanon-government-must-address-medication-shortages-and-healthcare-crisis/)). A substitute can be the same medicine under another brand name: that is the double dose Dalil catches.
- **Family far away:** 195,433 Lebanese emigrated between 2018 and 2021, 77,777 of them in 2021 alone (Information International estimates, cited by [LAU's Institute for Migration Studies, 2022](https://soas.lau.edu.lb/news/2022/01/the-lebanese-trend-of-emigration-a-new-peak-since-2019.php)).
- **What we did not find:** Lebanese data on how often patients take the same medicine under two brand names, or on whether reminders and family alerts improve adherence there. Dalil would need to measure both.

**Where Dalil sits in the day:** the patient already uses WhatsApp. Dalil sends the reminder at the dose time, the patient answers with one tap (or types 1, 2 or 3), and the family member abroad hears about a problem the same day. When a new box comes home from a doctor or the pharmacy, the patient sends one photo.

## What it does (demo story, fictional people)

Georges, 68, has high blood pressure, diabetes and a stomach problem. This week he has the flu: the ER gave him Tamiflu. His daughter Rita lives abroad.

1. **Reminder:** at 8:00 Dalil sends Georges his Gastrimut reminder in Arabic. He taps **Taken**. The dose is logged and the pill count goes down.
2. **Problem:** in the evening he taps **Problem** on his Amlor reminder, then **Ran out**. Rita gets an alert in English, taps **I'll check**, sees the reason and calls him.
3. **Photo:** the next day his GP prescribes Flumivir. Georges sends a photo of the box. Dalil reads it, asks "Is this Flumivir 75mg, box of 10?" with the official MoPH price, and he taps **Yes**.
4. **Double dose caught:** Flumivir and Tamiflu are the same medicine (oseltamivir) under two names. Dalil tells Georges not to take Flumivir before asking his doctor or pharmacist, and tells Rita too.

Also built: if a reminder gets no answer for 60 minutes, the dose is marked missed and Rita gets the same alert (silence is the worrying case: he forgot, feels unwell, or his phone is off). Typed replies work like the buttons: 1, 2, 3, or a word in Arabic, Arabizi or English. "Later" sends the reminder again 30 minutes later.

## Why AI, and why small

- **Reading the box:** a 16.2 MB OCR model (PaddleOCR PP-OCRv4, run with ONNX Runtime through RapidOCR) reads the printed name, strength and pack size. It runs on the CPU, with no GPU and no cloud. On our test set of 5 real Lebanese boxes plus 1 photo with no box, it got **6 of 6** right (brand and strength for each box, "not sure" for the photo with no box), in **about 0.3 to 0.6 s per photo** on a MacBook CPU, and the same 6 of 6 with Wi-Fi turned off (shown in the video). Run it yourself: `python -m scripts.eval_photos`. Six photos is a small test: a real evaluation needs many more boxes, photographed by older users in ordinary light.
- **Finding the medicine:** fuzzy matching (RapidFuzz) of the words read against the 5,762 brand names in the MoPH list, then the strength and pack size printed on the box pick the exact product.
- **Why a simpler tool would not do the job:** an older patient will not type "Flumivir 75mg", let alone "oseltamivir", correctly, and a plain reminder app does not know which brands are the same medicine. One photo replaces the typing: the match against the official list gives the exact product and its price, and our ingredient table links brands that share an active ingredient.
- **Understanding replies:** fixed keywords in English, Arabic and Arabizi, plus the numbers 1, 2 and 3. No chatbot and no large language model.

## Guardrails

- **A person makes the call.** Every box is confirmed by the patient (Yes / No) before Dalil uses it. The double-dose warning tells the patient to ask a doctor or pharmacist. Dalil never tells anyone to start, stop or change a dose, and gives no diagnosis.
- **"Not sure, ask a person" instead of guessing.** If the photo does not match a known medicine well, Dalil says "I'm not sure which medicine this is" and suggests a clearer photo or the pharmacist. If a medicine has no ingredient data, Dalil says it cannot check it yet. If a reply is not understood, Dalil asks again with numbered options.
- **Side effects:** Dalil tells the patient not to stop or change the medicine on their own, to ask their doctor or pharmacist, and to get medical help now if they feel very unwell. The caregiver is alerted.
- **Consent first, and STOP.** The first message from anyone explains, in Arabic and English, what Dalil saves and that it is not a doctor and never changes a dose. Nothing is sent or saved about medicines until the person taps Yes. Typing STOP (or وقف) stops all reminders and alerts at once.
- **Fixed messages:** every sentence Dalil can send is written in advance and reviewed, in each language.

## The AI works offline, on phones people already have

- The AI (OCR model, matching, MoPH list in SQLite) runs on one small machine with no internet needed for it. Only the WhatsApp messages travel over the network.
- Patients need nothing new: WhatsApp on the phone they have. Replies are one tap or one digit, so the same flow can run over plain SMS on a basic phone (the SMS gateway is not built yet).
- For a patient like Noor in the challenge brief, with a basic phone and a daughter's smartphone on weekends: SMS reminders on her phone, and the daughter as caregiver on WhatsApp.

## Local language

- **Lebanese Arabic** for the patient: approved Arabic WhatsApp templates, follow-up messages in Lebanese Arabic, and replies understood in Arabic script, Arabizi ("akhadt", "ba3den", "moshkle") and Arabic-Indic digits (١ ٢ ٣).
- **English** for the caregiver in the demo; each person gets their own language.
- **A less-supported language:** all messages are one table, so a new language means translating about 25 short sentences and getting 3 templates approved. The OCR reads printed Latin text, which is what Lebanese boxes carry; it does not read Arabic script.

## Data

| Dataset | Source | License | Size | Used for |
|---|---|---|---|---|
| Drugs Public Price List, marketed drugs, edition 11/8/2026 (updated 19/8/2026) | Lebanon Ministry of Public Health, https://www.moph.gov.lb/en/Pages/3/3101/drugs-public-price-list- | No license stated; not included in this repo (download it from the official link, see "Run it") | 5,762 drugs, 16 columns, 2.9 MB (.xls) | Brand names, strength, pack size, official price |
| Ingredient table (`data/ingredients_demo.csv`) | Made by the team from the MoPH Lebanon National Drugs Database pages | Ours, released with the code | 15 brands | Active ingredient and drug class for the duplicate check |
| OCR models (PP-OCRv4 detection + recognition, mobile v2.0 direction classifier) | PaddleOCR, packaged by RapidOCR (`rapidocr_onnxruntime` 1.4.4) | Apache-2.0 | 16.2 MB | Reading the box |
| Box photos (`data/boxes/`) | 5 boxes photographed by the team, plus 1 photo with no box | Ours | 6 photos | Evaluating the box reader (`scripts/eval_photos.py`) |
| Georges, Rita and their medicines | **Synthetic** demo data (`scripts/seed_demo.py`) | Ours | 2 people, 4 medicines | Demo |

**What the data does not cover:**

- The MoPH price list has no ingredient column. Ingredients are filled in for only 15 brands, so the duplicate check works only for those; any other medicine gets "I can't check this yet, ask your pharmacist".
- Only medicines on the MoPH marketed list: not medicines bought abroad, hospital-only drugs, supplements or herbal products.
- Prices are a snapshot from August 2026 and change often.
- No drug interaction data: Dalil only catches the same ingredient under two names. It is not a clinical decision tool.
- The OCR was tested on 6 photos (5 boxes with printed Latin text, 1 with no box). It does not read handwritten Arabic notes that pharmacists often write on boxes.
- Dalil has not been tested with real patients yet, so there is no measured effect on adherence.

## Privacy and consent

- **Where the data sits:** one SQLite file on the machine that runs Dalil (in the demo, the builder's laptop). It holds the phone number or WhatsApp ID, name, language, medicines, schedules, dose replies with reasons, and the caregiver link. Nothing goes to a cloud AI service.
- **Photos** are downloaded from WhatsApp, read in memory and not saved.
- **Who can read it:** whoever runs that machine (a clinic, an NGO, a pharmacy). A caregiver only receives alerts about the patient who is linked to them. Messages pass through Meta's WhatsApp Cloud API, which delivers them for Dalil.
- **If the phone is lost or shared:** the medicine list is on the server, not on the phone, but the WhatsApp chat on the phone shows the reminders and replies, and whoever holds the phone can answer them. STOP stops all reminders and alerts for that number; the stored data stays until the operator deletes it (a delete command is not built yet).
- **Consent:** the first message from any number is the consent message ("To remind you, I save your medicines, dose times and answers, and I can alert a family member you choose. I'm not a doctor and I never change a dose. Do you agree?"), with buttons for Arabic, English or No. A family member who types STOP gets no more alerts. In the demo, the two users and the family link were created by the seed script with the builder's consent; a setup chat where the patient picks the family member is not built yet.
- **Bias and inclusion:** Arabic messages use masculine forms by default because Dalil does not ask for gender yet; the OCR model was trained mainly on Chinese and English text.

## Built before the event (transparency)

Set up before Oct 3: the Meta app and WhatsApp test number, a webhook that greeted users, the database schema (7 tables), 6 WhatsApp message templates (approved Oct 2), an analysis of the MoPH list, and the choice of OCR engine after testing 5 boxes. Built during the event: loading the drug list and demo data, reminders and replies, caregiver alerts, the no-answer alert, photo reading and the duplicate check, consent and STOP, the photo evaluation script, the click-through demo page, this README and the videos. The git history shows the dates.

## Tech stack

Python 3.11, FastAPI, SQLite, WhatsApp Cloud API (Graph API v26.0), RapidOCR on ONNX Runtime, RapidFuzz, pandas and xlrd (to load the list), ngrok (to reach the laptop during the demo).

## Run it

```
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # fill in the WhatsApp keys and the two demo phone numbers
curl -L -o data/moph_marketed.xls "https://www.moph.gov.lb/userfiles/files/HealthCareSystem/Pharmaceuticals/DrugsPublicPriceList/11-8-2026/WebMarketed20260811-19-8-2026.xls"
python -m scripts.load_drugs   # reads data/moph_marketed.xls and data/ingredients_demo.csv
python -m scripts.seed_demo
python -m uvicorn app.main:app --port 8000
ngrok http 8000             # then set https://<your-domain>/webhook in the Meta app
```

Send a reminder now (for a demo): open `http://localhost:8000/demo/remind/<schedule id>?key=<VERIFY_TOKEN>`.

Score the box reader on the test photos: `python -m scripts.eval_photos`.

The click-through demo is one file, `docs/index.html`, with no build step. It replays the sentences in `app/texts.py` and the approved templates; open it in any browser.

## Scaling it

- **Another country:** replace `scripts/load_drugs.py` with a loader for that country's national drug list.
- **More ingredients:** import active ingredients and ATC codes for every brand from the MoPH Lebanon National Drugs Database, which would also allow same-class checks (two stomach-acid medicines, two blood-pressure medicines of the same kind).
- **Cost:** one small machine per clinic or NGO, and no AI service fees. WhatsApp charges per template message, at a rate that depends on the country and the message category (see Meta's rate card: https://developers.facebook.com/docs/whatsapp/pricing).

## Limits and next steps

SMS gateway for basic phones, voice-note reminders recorded by the caregiver, a setup chat (add medicines and the family member from WhatsApp), refill warnings from the pill count (the template is already approved), a delete-my-data command, checking the webhook signature (`X-Hub-Signature-256`) so only Meta can post to the server, reading the pharmacist's handwritten Arabic notes, asking for gender to fix Arabic grammar, and testing with patients and pharmacists in Lebanon.

## Your take

To me, localizing AI development means starting from the people who will use it, not from the model. For Dalil, that meant messages in Lebanese Arabic with replies understood in Arabizi, Lebanon's own Ministry of Public Health medicine list, and a 16 MB model that runs on an ordinary laptop. It also means being honest about limits: Dalil has not been tested with patients yet, and doing that with pharmacists in Lebanon is the next step.
