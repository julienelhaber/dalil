# Every message Dalil sends, in English and Lebanese Arabic.
TEXTS = {
    # Reminders (Step 2)
    "taken": {
        "en": "Logged: you took {medicine}. Thank you!",
        "ar": "تمام، سجّلت إنك أخدت {medicine}. الله يعطيك الصحة.",
    },
    "later": {
        "en": "OK, I'll remind you again in {minutes} minutes.",
        "ar": "ماشي، رح ذكّرك مرة تانية بعد {minutes} دقيقة.",
    },
    "problem": {
        "en": "What's the problem with {medicine}? If it's something else, type it.",
        "ar": "شو المشكلة مع {medicine}؟ إذا في شي تاني، اكتبلي ياه.",
    },
    "help": {
        "en": "Reply 1 if you took {medicine}, 2 to be reminded later, 3 if there is a problem.",
        "ar": "ردّ 1 إذا أخدت {medicine}، 2 إذا بدك ذكّرك بعدين، 3 إذا في مشكلة.",
    },
    # Reasons and family alerts (Step 3)
    "thanks": {
        "en": "Thanks for telling me. I let {names} know.",
        "ar": "شكراً إنك خبّرتني. بلّغت {names}.",
    },
    "thanks_alone": {
        "en": "Thanks for telling me. Your pharmacist can help.",
        "ar": "شكراً إنك خبّرتني. الصيدلي فيه يساعدك.",
    },
    "side_effect": {
        "en": "Don't stop or change {medicine} on your own: ask your doctor or pharmacist. If you feel very unwell, get medical help now.",
        "ar": "ما توقّف ولا تغيّر {medicine} لحالك، اسأل الحكيم أو الصيدلي. إذا حاسس حالك كتير تعبان، اطلب مساعدة طبية هلّق.",
    },
    "details": {
        "en": "{patient}'s answer: {reason}. Medicine: {medicine}, due at {time}. A call from you would help.",
        "ar": "جواب {patient}: {reason}. الدوا: {medicine}، موعدو الساعة {time}. اتصال منك بيساعد.",
    },
    "no_answer": {
        "en": "{patient} did not answer the reminder for {medicine} at {time}. A call from you would help.",
        "ar": "{patient} ما جاوب على تذكير {medicine} الساعة {time}. اتصال منك بيساعد.",
    },
    "checking": {
        "en": "Message from {name}: \"I'll check on you.\"",
        "ar": "رسالة من {name}: «رح إتطمّن عليك».",
    },
    # Medicine photo (Step 4)
    "not_sure": {
        "en": "I'm not sure which medicine this is. Send a clearer photo of the front of the box, or ask your pharmacist.",
        "ar": "مش متأكد شو هيدا الدوا. بعتلي صورة أوضح لقدّام العلبة، أو اسأل الصيدلي.",
    },
    "confirm": {
        "en": "Is this {name}, box of {pack}?",
        "ar": "هيدا {name}، علبة {pack}؟",
    },
    "price": {
        "en": "MoPH price: {price} LL",
        "ar": "سعر وزارة الصحة: {price} ل.ل.",
    },
    "declined": {
        "en": "OK, I didn't save it. Send a clearer photo, or ask your pharmacist.",
        "ar": "ماشي، ما سجّلتو. بعتلي صورة أوضح، أو اسأل الصيدلي.",
    },
    "unknown": {
        "en": "I can't check {new} against your other medicines yet. Ask your pharmacist before you start it.",
        "ar": "بعدني ما بقدر قارن {new} مع أدويتك التانية. اسأل الصيدلي قبل ما تبلّش فيه.",
    },
    "same": {
        "en": "Careful: {new} and {old} are the same medicine ({shared}) under two names. Taking both would double the dose. Don't take {new} before you ask your doctor or pharmacist.",
        "ar": "انتبه: {new} و{old} هني نفس الدوا ({shared}) بس باسمين مختلفين. إذا أخدت التنين، بتصير الجرعة دبل. ما تاخد {new} قبل ما تسأل الحكيم أو الصيدلي.",
    },
    "same_family": {
        "en": "Heads-up: {patient} sent a photo of {new}. It is the same medicine ({shared}) as {old}, which {patient} already takes. Taking both would double the dose. Please check with the doctor or pharmacist.",
        "ar": "تنبيه: {patient} بعت صورة {new}. هيدا نفس الدوا ({shared}) متل {old} اللي عم ياخدو. إذا أخد التنين، بتصير الجرعة دبل. تأكّد مع الحكيم أو الصيدلي.",
    },
    "added": {
        "en": "Added {new} to your list. Ask your pharmacist how and when to take it.",
        "ar": "زدت {new} عاللائحة. اسأل الصيدلي كيف وإيمتى لازم تاخدو.",
    },
    # Consent and help (Step 5)
    "consent_yes": {
        "en": "Thanks! I'll remind you when a dose is due, and you can send me a photo of a medicine box to check it. Type STOP at any time to stop everything.",
        "ar": "شكراً! رح ذكّرك بس يجي وقت الدوا، وفيك تبعتلي صورة علبة دوا لإفحصها. اكتب «وقف» بأي وقت لتوقّف كل شي.",
    },
    "stopped": {
        "en": "I stopped your reminders and alerts. Send me a message any time to start again.",
        "ar": "وقّفت التذكير والتنبيهات. إذا بدك ترجع، ابعتلي رسالة.",
    },
    "menu": {
        "en": "I'm Dalil. I remind you when a dose is due. Send me a photo of a medicine box to check it. Type STOP to stop everything.",
        "ar": "أنا دليل. بذكّرك بأدويتك بوقتها. ابعتلي صورة علبة دوا لإفحصها. اكتب «وقف» لتوقّف كل شي.",
    },
}

# First message to someone who has not agreed yet: both languages in one message
CONSENT_PROMPT = (
    "مرحبا! أنا دليل، بذكّرك بأدويتك عالواتساب. لحتى ذكّرك، بحفظ أدويتك ومواعيدها وأجوبتك، "
    "وفيني خبّر حدا من عيلتك إنت بتختارو. أنا مش حكيم وما بغيّر أي جرعة. بتوافق؟\n\n"
    "Hi! I'm Dalil, a medicine reminder on WhatsApp. To remind you, I save your medicines, "
    "dose times and answers, and I can alert a family member you choose. "
    "I'm not a doctor and I never change a dose. Do you agree?"
)
CONSENT_BUTTONS = [("CONSENT:ar", "نعم، بالعربي"), ("CONSENT:en", "Yes, in English"), ("CONSENT:no", "No / لا")]
CONSENT_NO = (
    "ماشي، ما رح ذكّرك وما رح احفظ أدويتك. إذا غيّرت رأيك، ابعتلي رسالة.\n\n"
    "OK, I won't remind you or save your medicines. If you change your mind, send me a message."
)
STOP_WORDS = {"stop", "وقف", "وقّف", "wa2ef", "wa22ef"}

REASON_BUTTONS = {
    "en": [("ran_out", "Ran out"), ("side_effect", "Side effect"), ("cost", "Too expensive")],
    "ar": [("ran_out", "خلص الدوا"), ("side_effect", "عوارض جانبية"), ("cost", "غالي كتير")],
}
YES_NO = {"en": ("Yes", "No"), "ar": ("إيه", "لا")}
DOSE_UNIT = {"en": "pill", "ar": "حبة"}

# Typed replies: one-character keys must match exactly,
# longer keys match the start of the word.
WORDS = {
    "TAKEN": {"1", "١", "taken", "took", "done", "akhad", "a5ad", "اخد", "أخد", "أخذ", "اخذ"},
    "LATER": {"2", "٢", "later", "ba3d", "بعد", "لاحق"},
    "PROBLEM": {"3", "٣", "problem", "moshk", "mushk", "mechk", "مشكل"},
}
# Access requests (Pilot 1): Arabic and English in one message, the language is not known yet
ACCESS_PENDING = (
    "أهلا! وصل طلبك لدليل. رح يوصلك مسج أول ما يجهز حسابك.\n\n"
    "Hi! Your request to use Dalil was sent. You'll get a message as soon as your access is ready."
)
ACCESS_WAITING = (
    "طلبك بعدو عم ينطر الموافقة. رح خبّرك أول ما يجهز.\n\n"
    "Your request is still waiting for approval. I'll tell you as soon as it's ready."
)
ACCESS_REJECTED = (
    "عذراً، دليل مش متاح إلك هلّق. شكراً لاهتمامك.\n\n"
    "Sorry, Dalil isn't available for you right now. Thanks for your interest."
)
# Messages to the admin (you), English only
ADMIN = {
    "new": "New request: {who}",
    "approved": "Approved {who}. They got the welcome message.",
    "approved_later": "Approved {who}. Their 24-hour window is closed, so they'll get the welcome when they write again.",
    "rejected": "Rejected {who}.",
    "already": "{who} is already {status}.",
    "none": "No pending requests.",
}
ADMIN_WORDS = {"pending", "requests"}
# Setup chat (Pilot 2)
SETUP = {
    "ask_name": {
        "en": "What's your name?",
        "ar": "شو اسمك؟",
    },
    "for_whom": {
        "en": "Nice to meet you, {name}! Who is Dalil for?",
        "ar": "تشرّفنا {name}! دليل لمين؟",
    },
    "tap_button": {
        "en": "Tap a button, or type 1 or 2.",
        "ar": "كبوس على زر، أو اكتب 1 أو 2.",
    },
    "ask_medicine": {
        "en": "Let's add the medicines one by one. Send me a photo of the first medicine box, or type its name.",
        "ar": "يلّا نزيد الأدوية وحدة وحدة. ابعتلي صورة علبة أول دوا، أو اكتب اسمو.",
    },
}
FOR_WHOM_BUTTONS = {
    "en": [("FOR:me", "For me"), ("FOR:family", "For a family member")],
    "ar": [("FOR:me", "إلي أنا"), ("FOR:family", "لحدا من العيلة")],
}
FOR_WHOM_WORDS = {"1": "me", "١": "me", "2": "family", "٢": "family"}
