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
    "declined": {  # PILOT 4: also mentions typing the name
        "en": "OK, I didn't save it. Send a clearer photo of the box, type the medicine name, or ask your pharmacist.",
        "ar": "ماشي، ما سجّلتو. ابعتلي صورة أوضح للعلبة، أو اكتب اسم الدوا، أو اسأل الصيدلي.",
    },
    "unknown": {
        "en": "Saved. Note: I can't check {new} against your other medicines for double doses yet. Ask your pharmacist if you're not sure.",
        "ar": "سجّلتو. بس انتبه: بعدني ما بقدر قارن {new} مع أدويتك التانية إذا في جرعة دبل. اسأل الصيدلي إذا مش متأكد.",
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
    "menu": {  # PILOT 4: typed names work after setup too
        "en": "I'm Dalil. I remind you when a dose is due. To add a medicine, send me a photo of the box or type its name. Type STOP to stop everything.",
        "ar": "أنا دليل. بذكّرك بأدويتك بوقتها. لتزيد دوا، ابعتلي صورة العلبة أو اكتب اسمو. اكتب «وقف» لتوقّف كل شي.",
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
    # PILOT 3: the medicine loop
    "ask_next": {
        "en": "Send me a photo of the next medicine box, or type its name.",
        "ar": "ابعتلي صورة علبة الدوا اللي بعدو، أو اكتب اسمو.",
    },
    "photo_no": {
        "en": "OK. Send a clearer photo of the box, or type the medicine name.",
        "ar": "ماشي. ابعتلي صورة أوضح للعلبة، أو اكتب اسم الدوا.",
    },
    "which": {
        "en": "Which one is it?",
        "ar": "أيّا واحد هو؟",
    },
    "choose": {
        "en": "Choose",
        "ar": "اختار",
    },
    "none_row": {
        "en": "Not in this list",
        "ar": "مش بهاللائحة",
    },
    "not_found": {
        "en": "I couldn't find \"{name}\" in the Ministry of Health list. Save it as you typed it, or type the name again?",
        "ar": "ما لقيت «{name}» بلائحة وزارة الصحة. بتحفظو متل ما كتبتو، أو بتكتب الاسم مرة تانية؟",
    },
    "retype": {
        "en": "OK, type the medicine name.",
        "ar": "ماشي، اكتب اسم الدوا.",
    },
    "ask_dose": {
        "en": "How much {medicine} do you take each time?",
        "ar": "قدّيش بتاخد من {medicine} كل مرة؟",
    },
    "dose_hint": {
        "en": "Tap a button, or type a number like 1 or 1.5.",
        "ar": "كبوس على زر، أو اكتب رقم متل 1 أو 1.5.",
    },
    "ask_time": {
        "en": "When do you take {medicine}? Choose a time.",
        "ar": "إيمتى بتاخد {medicine}؟ اختار الوقت.",
    },
    "time_hint": {
        "en": "Tap \"Choose a time\", or type a time like 8:30.",
        "ar": "كبوس على «اختار الوقت»، أو اكتب وقت متل 8:30.",
    },
    "time_button": {
        "en": "Choose a time",
        "ar": "اختار الوقت",
    },
    "type_time": {
        "en": "Type the time, like 8:30 or 21:00.",
        "ar": "اكتب الوقت، متل 8:30 أو 21:00.",
    },
    "bad_time": {
        "en": "I didn't get that time. Type it like 8:30 or 21:00.",
        "ar": "ما فهمت الوقت. اكتبو متل 8:30 أو 21:00.",
    },
    "time_saved": {
        "en": "Saved: {medicine} at {times}. Do you take it at another time too?",
        "ar": "سجّلت: {medicine} الساعة {times}. بتاخدو بوقت تاني كمان؟",
    },
    "med_saved": {
        "en": "{medicine}: {dose} at {times}. Add another medicine?",
        "ar": "{medicine}: {dose} الساعة {times}. بدك تزيد دوا تاني؟",
    },
    "next_or_done": {
        "en": "Add another medicine, or are you done?",
        "ar": "بدك تزيد دوا تاني، أو خلصت؟",
    },
    "saved_alone": {
        "en": "Saved: {medicine}, {dose} at {times}. I'll remind you at those times.",
        "ar": "سجّلت: {medicine}، {dose} الساعة {times}. رح ذكّرك بهالأوقات.",
    },
    "summary": {
        "en": "You're all set, {name}!\n\n{lines}\n\nYour first reminder is {first}. Type STOP at any time to stop everything.",
        "ar": "كل شي جاهز يا {name}!\n\n{lines}\n\nأول تذكير {first}. اكتب «وقف» بأي وقت لتوقّف كل شي.",
    },
    "line": {
        "en": "• {medicine}: {dose} at {times}",
        "ar": "• {medicine}: {dose} الساعة {times}",
    },
    "line_no_time": {
        "en": "• {medicine}: no reminder time yet",
        "ar": "• {medicine}: بعد ما في وقت للتذكير",
    },
    "today": {
        "en": "today at {time}",
        "ar": "اليوم الساعة {time}",
    },
    "tomorrow": {
        "en": "tomorrow at {time}",
        "ar": "بكرا الساعة {time}",
    },
    # PILOT 4: the family alert question ("For me" path)
    "family_ask": {
        "en": "Last question: should I tell someone in your family if you miss a dose?",
        "ar": "آخر سؤال: بدك خبّر حدا من عيلتك إذا ما أخدت دوا؟",
    },
    "family_name": {
        "en": "What's their name? You can also share their contact with me.",
        "ar": "شو اسم الشخص؟ فيك كمان تبعتلي الكونتاكت.",
    },
    "family_phone": {
        "en": "What's {family}'s WhatsApp number? For example 03 123 456 or +961 3 123 456.",
        "ar": "شو رقم الواتساب تبع {family}؟ متل 03 123 456 أو 961 3 123 456.",
    },
    "bad_phone": {
        "en": "That doesn't look like a phone number. Type it like 03 123 456. For a number outside Lebanon, start with + and the country code.",
        "ar": "هيدا ما بيشبه رقم تلفون. اكتبو متل 03 123 456. إذا الرقم برّا لبنان، ابدا بـ + ومفتاح البلد.",
    },
    "own_phone": {
        "en": "That's your own number. Type {family}'s number.",
        "ar": "هيدا رقمك إنت. اكتب رقم {family}.",
    },
    "family_linked": {
        "en": "Done: I'll tell {family} if you miss a dose.",
        "ar": "تمام: رح خبّر {family} إذا ما أخدت دوا.",
    },
    "family_invite": {
        "en": "Saved. Ask {family} to send \"hi\" to this WhatsApp number (you can forward my contact). Once {family} agrees, I'll tell them if you miss a dose.",
        "ar": "سجّلت. قول لـ{family} يبعت «hi» على هالرقم عالواتساب (فيك تبعتلو الكونتاكت تبعي). بس يوافق، رح خبّرو إذا ما أخدت دوا.",
    },
    "family_added_you": {
        "en": "{patient} added you as family on Dalil. If {patient} misses a dose, I'll send you a message.",
        "ar": "{patient} زادك كشخص من العيلة على دليل. إذا {patient} ما أخد دوا، رح بعتلك مسج.",
    },
    "family_ready": {
        "en": "You're set. If {patients} misses a dose, I'll send you a message.",
        "ar": "كل شي جاهز. إذا {patients} ما أخد دوا، رح بعتلك مسج.",
    },
    "family_agreed": {
        "en": "{family} agreed. I'll tell them if you miss a dose.",
        "ar": "{family} وافق. رح خبّرو إذا ما أخدت دوا.",
    },
}
FOR_WHOM_BUTTONS = {
    "en": [("FOR:me", "For me"), ("FOR:family", "For a family member")],
    "ar": [("FOR:me", "إلي أنا"), ("FOR:family", "لحدا من العيلة")],
}
FOR_WHOM_WORDS = {"1": "me", "١": "me", "2": "family", "٢": "family"}
# PILOT 3: buttons and menus of the medicine loop
NOT_FOUND_BUTTONS = {
    "en": [("MED_TYPED", "Save as typed"), ("MED_RETYPE", "Type it again")],
    "ar": [("MED_TYPED", "احفظو هيك"), ("MED_RETYPE", "بكتبو من جديد")],
}
DOSE_BUTTONS = {
    "en": [("DOSE:1", "1 pill"), ("DOSE:0.5", "Half a pill"), ("DOSE:2", "2 pills")],
    "ar": [("DOSE:1", "حبة وحدة"), ("DOSE:0.5", "نص حبة"), ("DOSE:2", "حبتين")],
}
TIME_ROWS = {
    "en": [("TIME:08:00", "Morning, 8:00"), ("TIME:14:00", "Noon, 14:00"), ("TIME:20:00", "Evening, 20:00"),
           ("TIME:22:00", "Bedtime, 22:00"), ("TIME:other", "Other time")],
    "ar": [("TIME:08:00", "الصبح، 8:00"), ("TIME:14:00", "الضهر، 14:00"), ("TIME:20:00", "المسا، 20:00"),
           ("TIME:22:00", "قبل النوم، 22:00"), ("TIME:other", "وقت تاني")],
}
MORE_TIME_BUTTONS = {
    "en": [("TIMES:more", "Yes, add a time"), ("TIMES:done", "No, that's all")],
    "ar": [("TIMES:more", "إيه، زيد وقت"), ("TIMES:done", "لا، هيك بس")],
}
MORE_MED_BUTTONS = {
    "en": [("MORE:add", "Add another"), ("MORE:done", "Done")],
    "ar": [("MORE:add", "زيد دوا"), ("MORE:done", "خلصت")],
}
# PILOT 4: the family alert question and typed answers
FAMILY_BUTTONS = {
    "en": [("FAMILY:yes", "Yes"), ("FAMILY:no", "No, thanks")],
    "ar": [("FAMILY:yes", "إيه"), ("FAMILY:no", "لا، شكراً")],
}
YES_WORDS = {"yes", "y", "eh", "ey", "aywa", "na3am", "إيه", "ايه", "اي", "أي", "نعم", "ايوا"}
NO_WORDS = {"no", "n", "la", "la2", "laa", "لا", "لأ", "كلا"}
DONE_WORDS = NO_WORDS | {"done", "finish", "finished", "that's all", "thats all", "khalas", "5alas",
                         "خلص", "خلصت", "خلاص"}
# Above the consent message for someone a patient added as family: both languages
INVITED = (
    "{patients} زادك على دليل لحتى تعرف إذا نسي دوا.\n"
    "{patients} added you on Dalil so you know if they miss a dose."
)
