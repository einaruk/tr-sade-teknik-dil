#!/usr/bin/env python3
"""Deterministic bilingual (English + Turkish) linter for the structural STE rules.

Derived from ste-lint.py of danyuchn/asd-ste100-skill v0.4.0 (MIT). The English
rules are unchanged. The Turkish rules are an adaptation of the same principles:
ASD-STE100 itself defines English only, so nothing here is "STE-compliant Turkish".

Checks only rules verifiable without a dictionary. Deliberately never flags
hedges or modality (may/might/could, -ebilir, olabilir, muhtemelen): the skill
treats confidence as content.

Usage:
    sade-lint.py FILE [FILE ...]
    echo "metin" | sade-lint.py [--json]
    sade-lint.py --lang tr FILE          # auto (default) | tr | en
    sade-lint.py --baseline 5 FILE       # pass unless hard violations exceed 5
    sade-lint.py --disable passive-voice,compound-tense FILE
    sade-lint.py --max-words-tr 20 --max-words-en 25 FILE
    sade-lint.py --allow "top kimde,dürt" FILE   # project glossary: approved terms
    sade-lint.py --selftest

Language is detected per line (table cell), with the file majority as fallback.
Exit 1 when hard ("advisory-free") violations exceed the baseline (default 0).
Advisory findings (passive voice, compound tenses) never fail the run.
"""
import json
import re
import sys
import unicodedata

# ----------------------------------------------------------------------------
# English rules — upstream, unchanged
# ----------------------------------------------------------------------------
# ponytail: regex heuristics, not a parser. No noun-cluster rule — needs POS
# tagging to avoid constant false positives; add spaCy-backed rule if ever needed.
# No ellipsis rule by owner's choice: technical writing sometimes earns one.
RULES = [
    ("semicolon", "advisory-free",
     re.compile(r";"),
     "STE bans the semicolon (Rule 8.1). Split into separate sentences."),
    ("phrasal-verb", "advisory-free",
     re.compile(r"\b(spin(?:ning|s)? up|spun up|reach(?:ing|es|ed)? out|div(?:e|es|ing|ed) into|dove into|kick(?:ing|s|ed)? off|circl(?:e|es|ing|ed) back|touch(?:ing|es|ed)? base)\b", re.I),
     "Soft phrasal verb. Use the single plain verb (start, contact, read, begin)."),
    ("marketing-adjective", "advisory-free",
     re.compile(r"\b(seamless(?:ly)?|robust(?:ly)?|cutting-edge|effortless(?:ly)?|blazing[- ]fast|world-class|state-of-the-art|game-chang(?:ing|er))\b", re.I),
     "Marketing adjective. Delete, or replace with the measurement that earns the claim."),
    ("nominalization", "advisory-free",
     re.compile(r"\b(perform|performs|performed|conduct|conducts|conducted|carry out|carries out|carried out)\s+(?:a|an|the)\s+\w+(?:tion|sion|ment|ance|ence|ysis)\b", re.I),
     "Action frozen into a noun. Use the verb (analyze, not perform an analysis of)."),
    ("passive-voice", "advisory",
     re.compile(r"\b(is|are|was|were|been|being)\s+(\w+ed|given|taken|made|done|found|seen|known|shown|written|built|sent|set|run|read|kept|held|left|put)\b(?!\s+(?:to|for|by)\s+\w+ing)", re.I),
     "Possible passive voice. Name the actor and use an active verb, unless the actor is unknown or irrelevant."),
    ("present-perfect", "advisory",
     # modal + perfect infinitive ("may have failed") is a protected hedge, not present perfect
     re.compile(r"(?<!\bmay )(?<!\bmight )(?<!\bcould )(?<!\bshould )(?<!\bwould )(?<!\bmust )\b(has|have|had)\s+(?:been\s+)?\w+(?:ed|en)\b", re.I),
     "Compound tense. Use simple past/present unless current relevance is the point (then keep and flag)."),
]

# One word, one meaning: groups of verbs commonly rotated for the same action.
# Only pairs where the members are genuinely interchangeable — error/fault/failure
# are distinct concepts and stay out.
SYNONYM_GROUPS = [
    ("check", "verify", "confirm", "validate"),
    ("delete", "remove", "erase"),
    ("start", "launch", "begin", "initiate"),
    ("stop", "halt", "terminate"),
    ("show", "display"),
    ("use", "utilize", "employ"),
    ("fix", "repair", "correct"),
    ("send", "transmit"),
    ("get", "retrieve", "fetch", "obtain"),
    ("change", "modify", "alter"),
]

MAX_WORDS = 25  # descriptions cap; instructions cap is 20 but undetectable without context
# Turkish is agglutinative: one word carries what English spreads over several.
# 18 is this skill's own heuristic (about 0.72 x 25), not a published standard.
MAX_WORDS_TR = 18

CODE_FENCE = re.compile(r"^(```|~~~)")
INLINE_CODE = re.compile(r"`[^`]*`")
LIST_ITEM_START = re.compile(
    r"^(?P<indent> {0,3})(?P<marker>[-*+]|[0-9]+[.)])(?P<gap> +)(?P<body>.*)$"
)
CONJUNCTION_END = re.compile(r"\b(?:and|or|ve|veya|ya da|yahut)\s*$", re.I)
TR_CONJUNCTIONS = {"ve", "veya", "ya da", "yahut"}
TABLE_SEPARATOR_CELL = re.compile(r"^:?-{3,}:?$")

# ----------------------------------------------------------------------------
# Turkish rules
# ----------------------------------------------------------------------------
L = "a-zçğıöşü"          # letters after tr_lower()
W = f"[{L}]"
VOW = "aeıioöuü"
_CIRCUMFLEX = str.maketrans("âîûÂÎÛ", "aiuaiu")


def tr_lower(s):
    """Length-preserving Turkish lowercase. str.lower() turns 'İ' into two chars
    and 'I' into 'i'; both break matching and columns."""
    return s.replace("İ", "i").replace("I", "ı").lower().translate(_CIRCUMFLEX)


# --- language detection ------------------------------------------------------
_TR_CHARS = set("çğıöşüÇĞİÖŞÜ")
_TR_STOP = {"ve", "bir", "bu", "için", "ile", "de", "da", "olarak", "değil", "veya",
            "her", "daha", "çok", "gibi", "sonra", "önce", "ise", "ya", "ne", "var",
            "yok", "en", "mi", "mı", "mu", "mü", "şu", "ama", "kadar", "göre", "ancak",
            "tüm", "hem", "ki", "ben", "sen", "biz", "siz", "lütfen", "evet", "hayır"}
_EN_STOP = {"the", "and", "is", "are", "of", "to", "in", "a", "an", "that", "it", "for",
            "with", "on", "this", "be", "as", "was", "were", "not", "or", "by", "from",
            "at", "if", "you", "must", "can", "will", "has", "have", "we", "then",
            "when", "do", "may", "should"}
_TR_SUFFIX = re.compile(r"(?:l[ae]r[ıi]?|[dt][ıiuü]r?|m[ae]k|[ıiuü]yor|[ae]c[ae]k|m[ıiuü]ş|"
                        r"[ıiuü]nd[ae]|[dt][ae]n|n[ıiuü]n|s[ıiuü]|y[ıiuü]|[ıiuü]n|[ıiuü]z)$")
_EN_SUFFIX = re.compile(r"(?:ing|tion|ed|ly|ous|ment)$")
_WORD = re.compile(r"[^\W\d_]+")


def _lang_scores(line):
    tr = en = 0.0
    for word in _WORD.findall(line):
        low_tr, low_en = tr_lower(word), word.lower()
        if any(ch in _TR_CHARS for ch in word):
            tr += 2
        elif low_tr in _TR_STOP:
            tr += 1
        elif low_en in _EN_STOP:
            en += 1
        elif len(word) > 4 and _EN_SUFFIX.search(low_en):
            en += 0.5
        elif len(word) > 4 and _TR_SUFFIX.search(low_tr):
            tr += 0.5
    return tr, en


def detect_lang(line):
    """Return 'tr', 'en', or None when the line gives no usable signal."""
    tr, en = _lang_scores(line)
    if tr > en:
        return "tr"
    if en > tr:
        return "en"
    return None


# --- sentence splitting ------------------------------------------------------
_TR_ABBR = {"vb", "vs", "vd", "örn", "bkz", "yak", "dr", "prof", "doç", "no", "md",
            "sn", "av", "tel", "mah", "cad", "sok", "ltd", "şti", "inc", "yy", "s"}
# closing markup may follow the mark: "**Kaydetme.** Sonra ..."
_SENT_END = re.compile(r"[.!?…]+[*_\"”’')\]]*(?=\s|$)")
_LEAD_MARKER = re.compile(r"^(\s*(?:>\s*)*(?:#{1,6}\s+|(?:[-*+]|\d+[.)])\s+)?(?:\[[ xX]\]\s+)?)")


def tr_sentences(line):
    """Split one line into (start_col, sentence). A period after an ordinal
    number ("3. satır") or an abbreviation ("vb.") does not end the sentence."""
    out, start = [], 0
    for m in _SENT_END.finditer(line):
        if m.start() < start:
            continue
        if m.group(0).startswith(".") and not m.group(0).startswith(".."):
            before = line[start:m.start()]
            token = before.rsplit(None, 1)[-1] if before.strip() else ""
            token = token.lstrip("([\"'")
            following = line[m.end():].lstrip()
            if token.isdigit() and following[:1].islower():
                continue
            if tr_lower(token) in _TR_ABBR:
                continue
        out.append((start, line[start:m.end()]))
        start = m.end() + (len(line[m.end():]) - len(line[m.end():].lstrip()))
    if line[start:].strip():
        out.append((start, line[start:]))
    return out


def _count_words(sentence):
    return sum(1 for token in sentence.split() if re.search(r"\w", token))


# --- passive voice -----------------------------------------------------------
# Turkish passive morphology: vowel-final stem -> -n, l-final stem -> -In,
# any other consonant -> -Il. No verb stem ends in b, so "-abil/-ebil"
# (ability, a protected hedge) never matches type A.
_NEGABIL = r"(?:[ae]bil|[ae]m[ae]|[ae]m[ıiuü](?=yor)|m[ae]|m[ıiuü](?=yor))?"
# "-dI" followed by "r" is the causative -dIr ("değerlendir-"), never a finite passive.
_TAIL = (r"(?:d[ıiuü](?!r)|m[ıiuü]ş|[ıiuü]r|y?[ae]c[ae][kğ]|[ıiuü]yor|yor|m[ae]k|"
         r"m[ae]l[ıi]|m[ae]s[ıi]|z|s[ıiuü]n)")
_STEM = rf"{W}*[{VOW}]{W}*?"
_PASS_A = re.compile(rf"^({_STEM}[cçdfgğhjkmnprsştvyz][ıiuü]l)({_NEGABIL}{_TAIL}{W}*)$")
_PASS_B = re.compile(rf"^({_STEM}l[ıiuü]n)({_NEGABIL}{_TAIL}{W}*)$")
_PASS_C = re.compile(rf"^({_STEM}l[ae]n|(?:ara|ata|ona|iste|dene|öde|oku|koru|tanı|tara|boya|sına)n)"
                     rf"({_NEGABIL}{_TAIL}{W}*)$")
# Nouns/adjectives in -Il plus copula, and lexicalised intransitive verbs.
_PASS_A_EXCL = {
    "değil", "okul", "tatil", "acil", "şekil", "nasıl", "profil", "dahil", "yeşil",
    "kızıl", "akıl", "gönül", "meşgul", "makul", "ödül", "temsil", "tahsil", "vekil",
    "kefil", "sefil", "müstakil", "hasıl", "fasıl", "mahsul", "fuzul", "ehil", "cahil",
    "sahil", "adil", "kamil", "sivil", "sicil", "tescil", "tadil", "katil", "fosil",
    "tekstil", "steril", "usul", "asıl", "oğul", "ışıl", "nesil",
    "katıl", "ayrıl", "yorul", "üzül", "bayıl", "kurtul", "dağıl", "yayıl", "sıkıl",
    "darıl", "sarıl", "takıl", "eğil", "dikil", "boğul", "süzül", "kıvrıl", "büzül",
    "yanıl", "devril", "doğrul", "koyul", "ayıl",
}
_PASS_B_EXCL = {"kalın", "gelin"}
_PASS_C_EXCL = {
    "kullan", "evlen", "hoşlan", "seslen", "ilgilen", "yararlan", "faydalan", "eğlen",
    "sallan", "yaslan", "ayaklan", "canlan", "şüphelen", "kaynaklan", "sinirlen",
    "heyecanlan", "hastalan", "yaşlan", "paslan", "kirlen", "ıslan", "şekillen",
    "sonuçlan", "hızlan", "endişelen", "borçlan", "odaklan", "katlan", "dinlen",
    "toparlan", "güçlen", "hareketlen", "nemlen", "üstlen",
}
# "bulun-" is "exist / be present" far more often than "be found".
_BULUN_PASSIVE = re.compile(r"^(?:d[uü]|[ae]m[ae]|m[ae]d|muş|[ae]c[ae][kğ])")
_PASS_AGENT = re.compile(r"\btaraf(?:ından|ımdan|ımızdan|ınızdan|larından|ımca|ımızca|ınızca|ınca|larınca)\b")
_TOKEN = re.compile(rf"{W}+")


def _is_passive(word):
    m = _PASS_A.match(word)
    if m and m.group(1) not in _PASS_A_EXCL:
        return True
    m = _PASS_B.match(word)
    if m:
        if m.group(1) == "bulun":
            return bool(_BULUN_PASSIVE.match(m.group(2)))
        if m.group(1) not in _PASS_B_EXCL:
            return True
    m = _PASS_C.match(word)
    return bool(m and m.group(1) not in _PASS_C_EXCL)


# --- compound / periphrastic tense -------------------------------------------
_MAKTA_EXCL = {"yemekte", "emekte", "ekmekte", "parmakta", "çakmakta", "ırmakta",
               "kaymakta", "damakta"}
_TR_COMPOUND = [
    re.compile(rf"\b{W}+m[ae]kt[ae](?:d[ıi]r(?:l[ae]r)?|y[ıi]m|y[ıi]z|s[ıi]n[ıi]z|l[ae]r|yd[ıi]{W}*)?(?![{L}])"),
    re.compile(rf"\b{W}+(?:m[ıiuü]ş|[ae]c[ae]k|[ıiuü]yor)\s+"
               rf"(?:ol(?:may)?[ıu]p|ol[ae]c[ae][kğ]{W}*|bulunm[ae]kt[ae]{W}*|bulunuyor{W}*|"
               rf"durumd[ae]{W}*|olm[ae]kt[ae]{W}*|olmuş{W}*|oldu{W}*)"),
]

# --- nominalization + empty light verb ---------------------------------------
_VN_EXCL = {"firma", "forma", "platforma", "norma", "sisteme", "döneme", "programa",
            "gündeme", "ortama", "probleme", "tema", "şema", "sinema", "diploma",
            "drama", "kelime", "cuma", "mahkeme", "tercüme", "dolma", "kıyma", "hurma",
            "sarma", "dondurma", "kavurma", "pastırma", "çizme", "düğme", "tekme"}
_YAP = r"yap(?!ı(?![lny])|ıl[ae]r(?![ıi])|ım|ay|ış|ıcı)"
_LIGHT = rf"(?:{_YAP}|gerçekleştir|icra\s+e[td]|yerine\s+getir)"
_ISLEM = r"(?:işlem(?:i|ini|leri|lerini|inin|lerinin)?\s+)?"
_TR_NOMINAL = [
    # -mA(sI) verbal noun + yap-/gerçekleştir-
    (re.compile(rf"\b(?P<noun>{W}{{2,}}m[ae]s[ıi](?:n[ıi]n?)?|{W}{{2,}}(?<![ıiuü])m[ae](?:l[ae]r[ıi]?|y[ıi])?)"
                rf"\s+{_ISLEM}{_LIGHT}{W}*"), True),
    # -Im / -Iş deverbal noun, "işlem", "analiz" ... + gerçekleştir-
    (re.compile(rf"\b(?:{W}+(?:[ıiuü]m|[ıiuü]ş)|işlem|analiz|kontrol|test|teslimat)"
                rf"(?:[ıiuü]|s[ıi]|l[ae]r[ıi]?)?(?:n[ıiuü]n?)?\s+{_ISLEM}gerçekleştir{W}*"), False),
    # object-marked verbal noun, up to three words, then the light verb:
    # "aktarımını üç aşamada gerçekleştirecek", "silme işlemini kim yerine getirecek"
    (re.compile(rf"\b(?:{W}+(?:m[ae]s[ıi]n[ıi]|(?<![ıiuü])m[ae]y[ıi]|[ıiuü]m[ıiuü]n[ıiuü]|[ıiuü]ş[ıiuü]n[ıiuü])|"
                rf"{W}+\s+işlem(?:ini|lerini))(?:\s+{W}+){{0,3}}?\s+"
                rf"(?:gerçekleştir|icra\s+e[td]|yerine\s+getir){W}*"), False),
    # "... işlemi yap-"
    (re.compile(rf"\b{W}+\s+işlem(?:i|ini|leri|lerini)\s+{_YAP}{W}*"), False),
    # common -Im deverbal nouns + yap- ("ölçüm yap" -> "ölç")
    (re.compile(rf"\b(?:ölçüm|seçim|çizim|gönderim|aktarım|kurulum|sayım|denetim|gözlem|dağıtım|teslimat)"
                rf"(?:[ıiuü]|l[ae]r[ıi]?)?(?:n[ıiuü])?\s+{_YAP}{W}*"), False),
    # genitive noun + "yapılması": "kabulünün yapılması" -> "kabul edilmesi"
    (re.compile(rf"\b(?:{W}+(?<![ıiuü])m[ae]n[ıi]n|(?:ölçüm|seçim|çizim|gönderim|aktarım|kurulum|sayım|"
                rf"denetim|gözlem|dağıtım|teslimat|kabul|test|işlem|kontrol){W}*n)\s+yapılma{W}*"), False),
    # "gerçekleştirilmesi süreci başlatılır" -> "gerçekleştirilir"
    (re.compile(rf"\b{W}+m[ae]s[ıi]\s+süreci{W}*\s+(?:başlat|yürüt|gerçekleştir|işlet){W}*"), False),
    # "-mAsI sağlan-", "kontrolünün sağlanması"
    (re.compile(rf"\b{W}+m[ae]s[ıi](?:n[ıi]n?)?\s+sağlan{W}*"), False),
    (re.compile(rf"\b(?:kontrol(?:ü|ünü|ünün)?|takip|takib(?:i|ini|inin)|teyit|teyid(?:i|ini|inin)|"
                rf"denetim(?:i|ini|inin)?|koordinasyon(?:u|unu|unun)?)\s+sağla{W}*"), False),
    # "incelemeye tabi tutuldu"
    (re.compile(rf"\b{W}+m[ae]y[ae]\s+tabi\s+tut{W}*"), False),
]

_MASINI_SAGLA = re.compile(rf"\b({W}+m[ae]s[ıi]n[ıi])\s+sağla{W}*")

# --- marketing adjectives ----------------------------------------------------
# "benzersiz" alone is the database sense ("unique"); it is marketing only
# in front of a product noun.
_UNIQUE_CLAIM = (r"\s+(?:bir\s+)?(?:deneyim|çözüm|ürün|fırsat|hizmet|platform|teknoloji|yaklaşım|"
                 r"tasarım|performans|kalite|avantaj|özellik|altyapı|mimari)")
_TR_MARKETING = re.compile(
    rf"\b(?:kusursuz{W}*|benzersiz{_UNIQUE_CLAIM}{W}*|eşsiz{W}*|rakipsiz{W}*|pürüzsüz{W}*|"
    rf"mükemmel{W}*|muhteşem{W}*|olağanüstü{W}*|harika{W}*|inanılmaz{W}*|muazzam{W}*|"
    rf"etkileyici{W}*|büyüleyici{W}*|çarpıcı{W}*|vazgeçilmez{W}*|fevkalade{W}*|şahane{W}*|"
    rf"zahmetsiz{W}*|yenilikçi{W}*|devrimsel{W}*|üstün(?![{L}])|"
    rf"çığır\s+aç(?:an|ıcı){W}*|devrim\s+(?:niteliğinde|yaratan)|ezber\s+bozan|"
    rf"oyun\s+değiştir{W}*|(?:en\s+)?son\s+teknoloji{W}*|en\s+gelişmiş|yeni\s+nesil|"
    rf"en\s+(?:yeni|modern|ileri)\s+teknoloji{W}*|kendini\s+kanıtlamış|"
    rf"dünya\s+(?:standartlarında|klasında)|birinci\s+sınıf|sınıfının\s+en\s+iyisi|"
    rf"(?:ışık|yıldırım|şimşek)\s+hızında|(?:ultra|süper)\s+hızlı|"
    rf"(?:sektör|pazar)\s+lideri{W}*|lider\s+çözüm{W}*|göz\s+(?:alıcı|kamaştırıcı)|"
    rf"nefes\s+kesici|eşi\s+benzeri\s+(?:olmayan|görülmemiş))"
)

# --- soft idiomatic verbs (the Turkish counterpart of phrasal verbs) ----------
_AT = r"at(?:t|ın|ar|ıyor|acak|mak|ma|alım|ıp|sın|abil|ayım)?(?![a-zçğıöşü])"
_AT = rf"at(?:(?:t|ın|ar|ıyor|acak|mak|ma|alım|ıp|sın|abil|ayım){W}*)?(?![{L}])"
_TR_IDIOM = re.compile(
    rf"\b(?:ayağa\s+kald[ıi]r{W}*|(?:bir\s+)?göz\s+{_AT}|göz\s+gezdir{W}*|hayata\s+geçir{W}*|"
    rf"hayat\s+bul{W}*|içine\s+dal{W}*|masaya\s+yat[ıi]r{W}*|el\s+{_AT}|elden\s+geçir{W}*|"
    rf"üstünden\s+geç{W}*|üzerinden\s+geç(?:elim|tik|eceğiz|iyoruz|mek|ip|erim|eyim|tim|eceğim|in|iniz)(?![{L}])|"
    rf"kolları\s+s[ıi]va{W}*|start\s+ver{W}*|rayına\s+otur{W}*|yoluna\s+koy{W}*|"
    rf"topu\s+(?:{W}+(?:['’]{W}+)?\s+)?{_AT}|top(?:u)?\s+(?:kimde|sizde|bizde|sende|bende|onda|onlarda)(?![{L}])|"
    rf"dürt(?!ü(?![{L}])|üs|üler){W}*|kafa\s+(?:yor|patlat){W}*|sıcak\s+bak{W}*|"
    rf"yeşil\s+ışık\s+(?:yak|ver){W}*|kaleme\s+al{W}*|dile\s+getir{W}*|mercek\s+altına\s+al{W}*|"
    rf"ince\s+eleyip\s+sık\s+doku{W}*|sahaya\s+(?:in|çık){W}*|taşın\s+altına|gaza\s+bas{W}*|"
    rf"vites\s+(?:yükselt|art[ıi]r|büyüt){W}*|nabız\s+yokla{W}*|taşlar[ıi]?\s+yerine\s+otur{W}*|"
    rf"su\s+yüzüne\s+çık{W}*|havada\s+kal{W}*|rafa\s+kald[ıi]r{W}*|sümen\s+altı{W}*|hasır\s+altı{W}*|"
    rf"(?:üstüne|üzerine)\s+gi[td]{W}*|peşine\s+düş{W}*|kulak\s+ver{W}*|ayak\s+uydur{W}*|"
    rf"el\s+ele\s+ver{W}*|omuz\s+ver{W}*|çözüme\s+kavuş{W}*|açıklığa\s+kavuş{W}*|"
    rf"netlik\s+kazan{W}*|ivme\s+kazan{W}*|hız\s+kazan{W}*|sonuca\s+bağla{W}*|"
    rf"gözden\s+kaç{W}*|işin\s+içinden\s+çık{W}*|altından\s+kalk{W}*|üstesinden\s+gel{W}*|"
    rf"ayak\s+sürü{W}*|baştan\s+sav{W}*|ipe\s+un\s+ser{W}*|yol\s+kat\s+e[td]{W}*)"
)

# --- officialese -------------------------------------------------------------
_TR_BUREAUCRATIC = [(re.compile(rf"\b(?:{pattern})"), plain) for pattern, plain in [
    (rf"mezkur{W}*", "söz konusu / bu"),
    (rf"işbu(?![{L}])", "bu"),
    (rf"müteakip{W}*|müteakiben|takiben(?![{L}])", "sonra / sonraki"),
    (rf"ivedilikle|ivedi(?![{L}])", "hemen / acil"),
    (rf"akabinde", "sonra / ardından"),
    (rf"tarafınız(?:a|ca)(?![{L}])", "size / siz"),
    (rf"tarafım(?:ız)?(?:a|ca)(?![{L}])", "bize / biz / bana / ben"),
    (rf"binaenaleyh|binaen(?![{L}])", "bu nedenle"),
    (rf"arz\s+(?:e[td]{W}*|olunur)", "bildiririm / rica ederim"),
    (rf"rica\s+olunur", "rica ederim"),
    (rf"bilgilerinize\s+(?:arz|sun){W}*", "bilginize"),
    (rf"gereğini\s+(?:rica|arz)", "gereğinin yapılmasını rica ederim"),
    (rf"husus{W}*", "konu / konusunda"),
    (rf"mevzubahis{W}*|mevzu\s+bahis|bahse\s+konu", "söz konusu"),
    (rf"zarfında", "içinde"),
    (rf"vasıtasıyla|marifetiyle", "ile / aracılığıyla"),
    (rf"nezdinde{W}*", "yanında / -de"),
    (rf"uhdesinde{W}*", "sorumluluğunda"),
    (rf"elzem{W}*", "gerekli"),
    (rf"zaruri{W}*", "zorunlu"),
    (rf"sehven", "yanlışlıkla"),
    (rf"zira(?![{L}])", "çünkü"),
    (rf"şayet", "eğer"),
    (rf"malum(?:unuz|ları){W}*", "bildiğiniz gibi"),
    (rf"istirham{W}*", "rica"),
    (rf"tensi[pb]{W}*", "uygun gör-"),
    (rf"olur(?:larınıza|unuza)", "onayınıza"),
    (rf"emirlerinize|takdirlerinize", "onayınıza / kararınıza"),
    (rf"hasebiyle", "nedeniyle"),
    (rf"mütevellit", "nedeniyle"),
    (rf"iştirak\s+e[td]{W}*", "katıl-"),
    (rf"ikmal\s+e[td]{W}*", "tamamla-"),
    (rf"ihtiva\s+e[td]{W}*", "içer-"),
    (rf"hasıl\s+ol{W}*", "ortaya çık-"),
    (rf"vuku\s+bul{W}*", "ol- / gerçekleş-"),
    (rf"ifa\s+e[td]{W}*|icra\s+e[td]{W}*", "yap-"),
    (rf"tevdi\s+e[td]{W}*", "ver- / teslim et-"),
    (rf"tanzim\s+e[td]{W}*", "düzenle-"),
    (rf"tebliğ\s+e[td]{W}*", "bildir-"),
    (rf"tatbik\s+e[td]{W}*", "uygula-"),
    (rf"takdim\s+e[td]{W}*", "sun-"),
    (rf"tetkik\s+e[td]{W}*", "incele-"),
    (rf"teşekkül\s+e[td]{W}*", "oluş-"),
    (rf"haiz(?![{L}])", "sahip"),
    (rf"münhasıran", "yalnızca"),
    (rf"bilahare", "sonra"),
    (rf"evvelemirde|evvela", "önce"),
    (rf"mukabilinde", "karşılığında"),
    (rf"mahiyetinde", "niteliğinde"),
    (rf"anılan(?![{L}])|zikredilen", "bu / belirtilen"),
    (rf"keza(?![{L}])", "ayrıca"),
    (rf"mamafih", "bununla birlikte"),
    (rf"mütalaa{W}*", "görüş"),
    (rf"istinaden|atfen(?![{L}])", "… üzerine / … nedeniyle"),
    (rf"ilişikte{W}*", "ekte"),
    (rf"muvacehesinde|meyanında|tahtında", "karşısında / arasında / altında"),
    (rf"tebellüğ{W}*", "teslim al-"),
    (rf"bilvesile|bu\s+vesileyle", "bu nedenle / ayrıca"),
    (rf"mucibince|gereğince(?![{L}])", "… uyarınca / … gereği"),
    (rf"yedinde{W}*", "elinde"),
    (rf"peyderpey", "aşama aşama"),
    (rf"ziyade(?![{L}])", "yerine / daha çok"),
    (rf"bittabi|filhakika|velhasıl", "elbette / gerçekten / kısacası"),
]]

# --- converb chains ("one instruction per sentence") --------------------------
# "olup olmadığı" means "whether": not a clause join.
_OLUP = re.compile(rf"\bol(?:may)?[ıu]p(?![{L}])(?!\s+olm)")
_IP = re.compile(rf"\b{W}{{2,}}[ıiuü]p(?![{L}])")
_IP_EXCL = {
    "sahip", "takip", "ekip", "grup", "kayıp", "ayıp", "garip", "galip", "mektup",
    "tertip", "prensip", "üslup", "talip", "klip", "kulüp", "kalıp", "rakip", "nasip",
    "tabip", "hatip", "katip", "mensup", "mahcup", "mağlup", "acayip", "yakup", "eyüp",
    "ragıp", "setup", "backup", "startup", "popup", "lookup", "markup", "group",
    "signup", "cleanup", "rollup", "pickup", "makeup", "mockup", "standup", "catchup",
    "followup", "checkup", "tulip", "olup", "olmayıp", "equip",
}
_CONVERBS = [
    re.compile(rf"\b{W}{{2,}}[ae]r[ae]k(?![{L}])"),
    re.compile(rf"\b{W}+[dt][ıiuü][kğ]t[ae]n\s+sonra(?![{L}])"),
    re.compile(rf"\b{W}+m[ae]d[ae]n\s+önce(?![{L}])"),
    re.compile(rf"\b{W}{{2,}}[ıiuü]nc[ae](?![{L}])"),
    re.compile(rf"\b{W}+(?:[ıiuü]r|[ae]r|yor|m[ıiuü]ş|[ae]c[ae]k|m[ae]z)ken(?![{L}])"),
]
_CONVERB_EXCL = {"olarak", "mübarek", "düşünce", "bilince", "sevince", "basınca"}


def _converbs(sentence):
    """Return [(col, word)] for every converb in a lowered sentence."""
    hits = []
    for m in _IP.finditer(sentence):
        word = m.group(0)
        if word in _IP_EXCL or word.endswith("ship"):
            continue
        # "uyup uymadığı", "okuyup okumadığı" mean "whether": one clause, not two
        following = re.match(rf"\s+({W}+)", sentence[m.end():])
        if following and any(following.group(1).startswith(stem + "m")
                             for stem in (word[:-2], word[:-3]) if len(stem) >= 2):
            continue
        hits.append((m.start(), word))
    for pattern in _CONVERBS:
        for m in pattern.finditer(sentence):
            if m.group(0) not in _CONVERB_EXCL:
                hits.append((m.start(), m.group(0)))
    return sorted(hits)


# --- one word, one meaning ---------------------------------------------------
def _tv(stem):
    """Consonant-final verb stem followed by a verbal suffix or a word end."""
    return (rf"\b{stem}(?=$|[^{L}]|m[ae]|m[ıiuü]ş|[dt][ıiuü]|[ıiuü]yor|[ae]c[ae]|"
            rf"[ıiuü][rlnp]|[ae]r|s[ıiuü]n|[ae]l[ıi]m|[ae]bil|[ae]m[ae]|[ae]y[ıi]m|"
            rf"[ae]n(?=$|[^{L}])|s[ae])")


def _tvv(stem, aorist=True):
    """Vowel-final verb stem. aorist=False where stem+r is also a noun plural
    ("ekler", "görüntüler", "yollar")."""
    after = "mdrynl" if aorist else "mdyn"
    return (rf"\b(?:{stem}(?=$|[^{L}]|[{after}]|s[ıiuü]n|c[ae])|{stem[:-1]}[ıiuü]yor)")


def _tet(noun):
    return rf"\b{noun}\s+e[td]"


TR_SYNONYM_GROUPS = [
    # "kimlik doğrulama" (authentication) is a term, not the verb
    [("kontrol et", _tet("kontrol")), ("doğrula", r"(?<!kimlik )" + _tvv("doğrula")),
     ("teyit et", r"\bteyi[td]\s+e[td]")],
    [("sil", _tv("sil")), ("kaldır", r"(?<!ayağa )(?<!rafa )" + _tv("kaldır"))],
    [("durdur", _tv("durdur")), ("sonlandır", _tv("sonlandır"))],
    [("göster", _tv("göster")), ("görüntüle", _tvv("görüntüle", aorist=False))],
    [("kullan", _tv("kullan")), ("yararlan", _tv("yararlan")), ("faydalan", _tv("faydalan"))],
    [("düzelt", _tv("düzelt")), ("onar", _tv("onar")), ("tamir et", _tet("tamir"))],
    [("gönder", _tv("gönder")), ("ilet", _tv("ilet")), ("yolla", _tvv("yolla", aorist=False))],
    [("değiştir", _tv("değiştir")), ("tadil et", _tet("tadil")), ("modifiye et", _tet("modifiye"))],
    [("ekle", _tvv("ekle", aorist=False)), ("ilave et", _tet("ilave"))],
    [("oluştur", _tv("oluştur")), ("yarat", _tv("yarat"))],
    [("tamamla", _tvv("tamamla")), ("bitir", _tv("bitir")), ("sonuçlandır", _tv("sonuçlandır"))],
    [("bildir", _tv("bildir")), ("haber ver", r"\bhaber\s+ver"), ("bilgilendir", _tv("bilgilendir"))],
    [("incele", _tvv("incele")), ("gözden geçir", r"\bgözden\s+geçir")],
    [("iste", rf"\b(?:iste(?!mci)(?=$|[^{L}]|[mdrynl]|s[ıiuü]n|c[ae])|ist[ıi]yor)"),
     ("talep et", _tet("talep"))],
]
TR_SYNONYM_GROUPS = [[(base, re.compile(pattern)) for base, pattern in group]
                     for group in TR_SYNONYM_GROUPS]

TR_MSG = {
    "semicolon": "Noktalı virgül kullanma (STE Kural 8.1). İki ayrı cümle yaz.",
    "passive-voice": "Edilgen olabilir. İşi yapanı özne yap, etken fiil kullan (fail bilinmiyor ya da önemsizse kalabilir).",
    "passive-agent": "'tarafından' faili zaten söylüyor. Faili özne yap, etken yaz.",
    "compound-tense": "Birleşik zaman. Yalın zaman kullan (-mektedir → -ir/-iyor, -mış bulunmaktadır → -dı).",
    "nominalization": "İsimleştirme + boş fiil. Tek fiil kullan (inceleme gerçekleştirildi → incelendi).",
    "marketing-adjective": "Pazarlama sıfatı. Sil ya da iddiayı kanıtlayan ölçümü yaz.",
    "phrasal-verb": "Deyimsel fiil. Tek, yalın fiil kullan (ayağa kaldır → başlat, göz at → oku).",
    "bureaucratic": "Ağdalı/resmî ifade. Gündelik karşılığını kullan: {plain}.",
    "olup": "'olup' iki cümleyi birleştiriyor. Noktayla böl.",
    "clause-chain": "Tek cümlede {n} ulaç var. Her işi ayrı cümle yap.",
    "long-sentence": "Cümle {n} kelime (sınır {cap}). Böl.",
    "synonym-rotation": "'{base}' ve '{first}' aynı işi anlatıyor. Birini seç, her yerde onu kullan.",
    "dangling-conjunction": "Liste maddesi bağlaçla bitiyor. Maddeyi tamamla ya da sonraki maddeyle birleştir.",
}

_URL = re.compile(r"https?://\S+|\]\([^)]*\)")


def _mask(match):
    return " " * len(match.group(0))


# A bare -mIş / -AcAk passive directly before another word is usually a participle
# used as an adjective ("onaylanmış doküman", "yapılacak işler"), which STE allows.
_BARE_PARTICIPLE = re.compile(r"(?:m[ıiuü]ş|[ae]c[ae]k)$")
_AFTER_FINITE = {"ama", "ve", "fakat", "ancak", "veya", "ya", "ki", "mı", "mi", "mu", "mü",
                 "değil", "olabilir", "olmalı", "gibi", "ise", "diye", "çünkü", "lakin",
                 "ayrıca", "sonra", "ardından", "de", "da", "bile", "zaten", "olup",
                 "olacak", "oldu", "olduğu", "olması", "bulunmaktadır", "bulunuyor",
                 "durumda", "durumdadır"}
_BLOCK_BREAK = re.compile(r"^\s*(?:#{1,6}\s|[-*_]{3,}\s*$|[A-Za-z_][\w-]*:(?:\s|$))")


def _lint_tr_block(pieces, filename, seen, max_words):
    """Lint one Turkish paragraph: [(lineno, source_column, text)]. A table cell is
    a block of one piece. Hard-wrapped lines are joined so that a sentence or a
    phrase split across lines is still seen whole. Code spans, URLs and list
    markers are masked, not removed, so columns stay aligned with the source."""
    findings = []
    texts, starts, offset = [], [], 0
    for lineno, source_column, segment in pieces:
        masked = _URL.sub(_mask, INLINE_CODE.sub(_mask, segment))
        masked = _LEAD_MARKER.sub(_mask, masked, count=1)
        starts.append((offset, lineno, source_column))
        texts.append(masked)
        offset += len(masked) + 1
    joined = " ".join(texts)
    low = tr_lower(joined)

    def add(rule, level, position, match, message):
        start, lineno, source_column = next(s for s in reversed(starts) if s[0] <= position)
        findings.append({"file": filename, "line": lineno,
                         "col": source_column + position - start + 1,
                         "rule": rule, "level": level, "match": match,
                         "message": message, "lang": "tr"})

    for m in re.finditer(";", low):
        add("semicolon", "advisory-free", m.start(), ";", TR_MSG["semicolon"])
    tokens = list(_TOKEN.finditer(low))
    for index, m in enumerate(tokens):
        if not _is_passive(m.group(0)):
            continue
        if m.group(0) == "okunur" and index and tokens[index - 1].group(0) == "salt":
            continue  # "salt okunur" = read-only
        if _BARE_PARTICIPLE.search(m.group(0)) and index + 1 < len(tokens):
            following = tokens[index + 1]
            if (not low[m.end():following.start()].strip(" \t[(\"'“‘*_")
                    and following.group(0) not in _AFTER_FINITE):
                continue
        add("passive-voice", "advisory", m.start(), m.group(0), TR_MSG["passive-voice"])
    for m in _PASS_AGENT.finditer(low):
        add("passive-voice", "advisory", m.start(), m.group(0), TR_MSG["passive-agent"])
    for pattern in _TR_COMPOUND:
        for m in pattern.finditer(low):
            if m.group(0) not in _MAKTA_EXCL:
                add("compound-tense", "advisory", m.start(), m.group(0), TR_MSG["compound-tense"])
    nominal_spans = []
    for pattern, has_noun in _TR_NOMINAL:
        for m in pattern.finditer(low):
            if has_noun and m.group("noun") in _VN_EXCL:
                continue
            if any(m.start() < end and start < m.end() for start, end in nominal_spans):
                continue
            nominal_spans.append((m.start(), m.end()))
            add("nominalization", "advisory-free", m.start(), m.group(0), TR_MSG["nominalization"])
    # "doğrulanmasını sağlayın" -> "doğrulayın": only when the verbal noun is passive
    for m in _MASINI_SAGLA.finditer(low):
        if _is_passive(m.group(1)) and not any(
                m.start() < end and start < m.end() for start, end in nominal_spans):
            add("nominalization", "advisory-free", m.start(), m.group(0), TR_MSG["nominalization"])
    for m in _TR_MARKETING.finditer(low):
        add("marketing-adjective", "advisory-free", m.start(), m.group(0), TR_MSG["marketing-adjective"])
    for m in _TR_IDIOM.finditer(low):
        add("phrasal-verb", "advisory-free", m.start(), m.group(0), TR_MSG["phrasal-verb"])
    for pattern, plain in _TR_BUREAUCRATIC:
        for m in pattern.finditer(low):
            add("bureaucratic", "advisory-free", m.start(), m.group(0),
                TR_MSG["bureaucratic"].format(plain=plain))
    for m in _OLUP.finditer(low):
        add("clause-chain", "advisory-free", m.start(), m.group(0), TR_MSG["olup"])

    for start, sentence in tr_sentences(joined):
        n = _count_words(sentence)
        if n > max_words:
            add("long-sentence", "advisory-free", start, f"{n} words",
                TR_MSG["long-sentence"].format(n=n, cap=max_words))
        hits = _converbs(tr_lower(sentence))
        if len(hits) >= 2:
            add("clause-chain", "advisory-free", start + hits[0][0],
                ", ".join(word for _, word in hits),
                TR_MSG["clause-chain"].format(n=len(hits)))

    for gi, group in enumerate(TR_SYNONYM_GROUPS):
        for base, pattern in group:
            if (gi, base) in seen:
                continue
            m = pattern.search(low)
            if m:
                start, lineno, source_column = next(
                    s for s in reversed(starts) if s[0] <= m.start())
                seen[(gi, base)] = (lineno, source_column + m.start() - start + 1, base)
    return findings, len(joined.split())


# ----------------------------------------------------------------------------
# Shared machinery (upstream)
# ----------------------------------------------------------------------------
def _word_re(base):
    return re.compile(r"\b" + base + r"(?:s|es|ed|d|ing)?\b", re.I)


def _leading_spaces(line):
    return len(line) - len(line.lstrip(" "))


def _is_list_continuation(line, content_indent):
    if not line.strip():
        return True
    if LIST_ITEM_START.match(line):
        return False
    return _leading_spaces(line) >= content_indent


def _split_table_row(line):
    """Return trimmed table cells and their zero-based source columns.

    A pipe must separate at least two cells. Escaped pipes stay in their cell.
    This deliberately implements only the ordinary Markdown table shape; it is
    enough to distinguish a table from prose that happens to contain a pipe.
    """
    left = len(line) - len(line.lstrip())
    right = len(line.rstrip())
    content = line[left:right]
    if "|" not in content:
        return None
    if content.startswith("|"):
        content = content[1:]
        left += 1
    if content.endswith("|"):
        content = content[:-1]
    raw_cells = re.split(r"(?<!\\)\|", content)
    if len(raw_cells) < 2:
        return None

    cells = []
    column = left
    for raw_cell in raw_cells:
        leading = len(raw_cell) - len(raw_cell.lstrip())
        cells.append((raw_cell.strip(), column + leading))
        column += len(raw_cell) + 1
    return cells


def _markdown_table_cells(lines):
    """Map ordinary Markdown table rows to their prose cells.

    The separator row anchors detection, so pipe-containing prose is not
    treated as a table. Both leading-pipe and no-leading-pipe table styles are
    accepted when their header and body use the same number of cells.
    """
    table_cells = {}
    index = 1
    while index < len(lines):
        separator = _split_table_row(lines[index])
        header = _split_table_row(lines[index - 1])
        if (not separator or not header or len(separator) != len(header)
                or not all(TABLE_SEPARATOR_CELL.fullmatch(cell)
                           for cell, _ in separator)):
            index += 1
            continue

        table_cells[index - 1] = header
        table_cells[index] = []
        index += 1
        while index < len(lines):
            row = _split_table_row(lines[index])
            if not row or len(row) != len(separator):
                break
            table_cells[index] = row
            index += 1
    return table_cells


def _dangling_conjunction_findings(text, filename):
    lines = text.splitlines()
    findings = []
    in_fence = False
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if CODE_FENCE.match(stripped):
            in_fence = not in_fence
            index += 1
            continue
        if in_fence:
            index += 1
            continue
        start = LIST_ITEM_START.match(line)
        if not start:
            index += 1
            continue

        content_indent = (len(start.group("indent"))
                          + len(start.group("marker"))
                          + len(start.group("gap")))
        item_lines = [(index, start.group("body"))]
        next_index = index + 1
        item_fence = False
        while next_index < len(lines):
            candidate = lines[next_index]
            candidate_stripped = candidate.strip()
            if CODE_FENCE.match(candidate_stripped):
                # Fence delimiters are state markers, not meaningful item lines.
                item_fence = not item_fence
                next_index += 1
                continue
            if item_fence:
                next_index += 1
                continue
            if not _is_list_continuation(candidate, content_indent):
                break
            item_lines.append((next_index, candidate))
            next_index += 1

        meaningful = []
        for line_index, item_line in item_lines:
            # Preserve code spans as neutral operands while ignoring their contents.
            cleaned = INLINE_CODE.sub(" CODE ", item_line).strip()
            if cleaned:
                meaningful.append((line_index, cleaned))
        if meaningful:
            end_line_index, end_line = meaningful[-1]
            conjunction = CONJUNCTION_END.search(end_line)
        else:
            end_line_index, end_line, conjunction = None, None, None
        if conjunction:
            if end_line_index == index:
                finding_line = index + 1
                finding_col = start.start("marker") + 1
            else:
                raw_end_line = next(
                    raw for line_index, raw in item_lines
                    if line_index == end_line_index
                )
                masked_end_line = INLINE_CODE.sub(
                    lambda match: " " * len(match.group(0)), raw_end_line
                )
                raw_conjunction = CONJUNCTION_END.search(masked_end_line)
                finding_line = end_line_index + 1
                finding_col = raw_conjunction.start() + 1 if raw_conjunction else 1
            is_tr = tr_lower(conjunction.group(0).strip()) in TR_CONJUNCTIONS
            findings.append({
                "file": filename,
                "line": finding_line,
                "col": finding_col,
                "rule": "dangling-conjunction",
                "level": "advisory-free",
                "match": end_line,
                "message": (TR_MSG["dangling-conjunction"] if is_tr else
                            "List item ends with a coordinating conjunction. Complete the item or join it with the next item."),
                "lang": "tr" if is_tr else "en",
            })
        index = next_index
    return findings


def _file_lang(lines):
    tr = en = 0.0
    in_fence = False
    for line in lines:
        if CODE_FENCE.match(line.strip()):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        line_tr, line_en = _lang_scores(INLINE_CODE.sub("", line))
        tr += line_tr
        en += line_en
    return "tr" if tr > en else "en"


_QUOTE_PREFIX = re.compile(r"^\s*(?:>\s?)+")


def _plan_blocks(lines, table_cells, lang, default_lang):
    """Group prose lines into paragraphs and pick a language for each line.

    Returns one (block_id, lang) per prose line and None for blank, fenced and
    table lines. A hard-wrapped line often carries too little signal on its own
    ("Kaynak: Northwind Modernization teklifi"), so a line follows its paragraph
    unless the line itself is clearly in the other language."""
    plan = [None] * len(lines)
    blocks, current, in_fence = [], [], False

    def close():
        if current:
            blocks.append(list(current))
            current.clear()

    for index, line in enumerate(lines):
        if CODE_FENCE.match(line.strip()):
            in_fence = not in_fence
            close()
            continue
        if in_fence:
            continue
        if index in table_cells or not line.strip():
            close()
            continue
        if current:
            previous = lines[current[-1]]
            body = _QUOTE_PREFIX.sub("", line)
            if (LIST_ITEM_START.match(body) or _BLOCK_BREAK.match(body)
                    or bool(_QUOTE_PREFIX.match(line)) != bool(_QUOTE_PREFIX.match(previous))
                    or previous.rstrip().endswith(":")
                    or _QUOTE_PREFIX.sub("", previous).lstrip().startswith("#")):
                close()
        current.append(index)
    close()
    for block_id, indexes in enumerate(blocks):
        block_lang = lang
        if lang == "auto":
            block_lang = detect_lang(
                " ".join(INLINE_CODE.sub("", lines[i]) for i in indexes)) or default_lang
        for i in indexes:
            line_lang = block_lang
            if lang == "auto":
                tr, en = _lang_scores(INLINE_CODE.sub("", lines[i]))
                if abs(tr - en) >= 1.5:
                    line_lang = "tr" if tr > en else "en"
            plan[i] = (block_id, line_lang)
    return plan


def lint(text, filename="<stdin>", lang="auto", max_words_en=MAX_WORDS,
         max_words_tr=MAX_WORDS_TR):
    text = unicodedata.normalize("NFC", text)
    findings = []
    words_total = 0
    in_fence = False
    lines = text.splitlines()
    table_cells = _markdown_table_cells(lines)
    default_lang = lang if lang != "auto" else _file_lang(lines)
    # first occurrence of each synonym-group member: (group_idx, base) -> (line, col, match)
    seen_synonyms = {}
    seen_synonyms_tr = {}
    plan = _plan_blocks(lines, table_cells, lang, default_lang)
    tr_block = []  # Turkish prose lines of the current paragraph
    tr_block_id = None

    def flush():
        if not tr_block:
            return 0
        tr_findings, tr_words = _lint_tr_block(
            tr_block, filename, seen_synonyms_tr, max_words_tr)
        findings.extend(tr_findings)
        tr_block.clear()
        return tr_words

    for lineno, raw_line in enumerate(lines, 1):
        if CODE_FENCE.match(raw_line.strip()):
            in_fence = not in_fence
            words_total += flush()
            continue
        if in_fence:
            continue
        is_table = (lineno - 1) in table_cells
        segments = table_cells.get(lineno - 1, [(raw_line, 0)])
        for segment, source_column in segments:
            if is_table:
                segment_lang = lang if lang != "auto" else (
                    detect_lang(INLINE_CODE.sub("", segment)) or default_lang)
                block_id = None
            elif plan[lineno - 1] is None:  # blank line
                words_total += flush()
                continue
            else:
                block_id, segment_lang = plan[lineno - 1]
            if segment_lang == "tr":
                if is_table or block_id != tr_block_id:
                    words_total += flush()
                tr_block.append((lineno, source_column, segment))
                tr_block_id = block_id
                if is_table:
                    words_total += flush()
                continue
            words_total += flush()
            line = INLINE_CODE.sub("", segment)
            words_total += len(line.split())
            for rule_id, level, pattern, msg in RULES:
                for m in pattern.finditer(line):
                    findings.append({"file": filename, "line": lineno,
                                     "col": source_column + m.start() + 1,
                                     "rule": rule_id, "level": level,
                                     "match": m.group(0), "message": msg, "lang": "en"})
            for gi, group in enumerate(SYNONYM_GROUPS):
                for base in group:
                    if (gi, base) in seen_synonyms:
                        continue
                    m = _word_re(base).search(line)
                    if m:
                        seen_synonyms[(gi, base)] = (
                            lineno, source_column + m.start() + 1, m.group(0)
                        )
            for sent in re.split(r"(?<=[.!?])\s+", line):
                n = len(sent.split())
                if n > max_words_en:
                    findings.append({"file": filename, "line": lineno,
                                     "col": source_column + 1,
                                     "rule": "long-sentence", "level": "advisory-free",
                                     "match": f"{n} words",
                                     "message": f"Sentence has {n} words (cap {max_words_en}). Split it.",
                                     "lang": "en"})
    words_total += flush()
    # synonym rotation: flag each member after the first, at its first occurrence
    for gi, group in enumerate(SYNONYM_GROUPS):
        present = [(seen_synonyms[(gi, b)], b) for b in group if (gi, b) in seen_synonyms]
        if len(present) > 1:
            present.sort()  # document order
            first_base = present[0][1]
            for (lineno, col, match), base in present[1:]:
                findings.append({"file": filename, "line": lineno, "col": col,
                                 "rule": "synonym-rotation", "level": "advisory-free",
                                 "match": match,
                                 "message": f"'{base}' and '{first_base}' name the same action. Pick one and use it every time.",
                                 "lang": "en"})
    for gi, group in enumerate(TR_SYNONYM_GROUPS):
        present = [(seen_synonyms_tr[(gi, b)], b) for b, _ in group if (gi, b) in seen_synonyms_tr]
        if len(present) > 1:
            present.sort()
            first_base = present[0][1]
            for (lineno, col, match), base in present[1:]:
                findings.append({"file": filename, "line": lineno, "col": col,
                                 "rule": "synonym-rotation", "level": "advisory-free",
                                 "match": match,
                                 "message": TR_MSG["synonym-rotation"].format(base=base, first=first_base),
                                 "lang": "tr"})
    findings.extend(_dangling_conjunction_findings(text, filename))
    findings.sort(key=lambda f: (f["line"], f["col"]))
    return findings, words_total


def report(findings, words_total, as_json, hard_count, baseline):
    rate = round(len(findings) * 100 / words_total, 1) if words_total else 0.0
    if as_json:
        print(json.dumps({"violations": findings, "count": len(findings),
                          "hard_count": hard_count, "baseline": baseline,
                          "words": words_total, "per_100_words": rate},
                         indent=2, ensure_ascii=False))
        return
    for f in findings:
        print(f"{f['file']}:{f['line']}:{f['col']} {f['rule']}: {f['message']} [{f['match']}]")
    print(f"\n{len(findings)} violations ({hard_count} hard, baseline {baseline}), "
          f"{words_total} words, {rate} per 100 words")
    print("Hedges/modality (may, might, could, -ebilir, olabilir) are never flagged: confidence is content.")


def _rules(text, **kwargs):
    return {f["rule"] for f in lint(text, **kwargs)[0]}


def selftest():
    # ---- English: upstream assertions, unchanged ----
    bad = ("The panel is removed; spin up the job. "
           "Perform an analysis of the seamless log. "
           "We have received the report.")
    findings, _ = lint(bad)
    rules = {f["rule"] for f in findings}
    for expected in ("semicolon", "phrasal-verb", "nominalization",
                     "marketing-adjective", "passive-voice", "present-perfect"):
        assert expected in rules, expected
    # hedges must never be flagged, including modal + perfect infinitive
    findings, _ = lint("The request may have failed. It could be a timeout. "
                       "The disk might have filled.")
    assert findings == [], findings
    # code blocks skipped
    findings, _ = lint("```\nx = a; y = b\n```")
    assert findings == []
    # all supported list markers, case variants, and trailing whitespace
    findings, _ = lint(
        "- Confirm the target and\n"
        "* Record the result OR  \n"
        "+ Close the panel\n"
        "1. Start the task and\n"
        "2) Stop the task OR"
    )
    dangling = [f for f in findings if f["rule"] == "dangling-conjunction"]
    assert len(dangling) == 4, dangling
    assert [f["line"] for f in dangling] == [1, 2, 4, 5], dangling
    assert [f["col"] for f in dangling] == [1, 1, 1, 1], dangling
    assert all(f["level"] == "advisory-free" for f in dangling), dangling

    # valid continuation lines and standalone four-space code are ignored
    findings, _ = lint("  - Confirm the target and\n    record the result.")
    assert not any(f["rule"] == "dangling-conjunction" for f in findings)
    findings, _ = lint("- Confirm the target\n  and")
    dangling = [f for f in findings if f["rule"] == "dangling-conjunction"]
    assert len(dangling) == 1 and dangling[0]["line"] == 2, dangling
    assert dangling[0]["col"] == 3, dangling
    findings, _ = lint("    - code and")
    assert not any(f["rule"] == "dangling-conjunction" for f in findings)
    findings, _ = lint("> - Confirm the target and\n> - Record the result or")
    assert not any(f["rule"] == "dangling-conjunction" for f in findings)
    findings, _ = lint("- Do this and\n~~~\ncode and\n~~~")
    dangling = [f for f in findings if f["rule"] == "dangling-conjunction"]
    assert len(dangling) == 1 and dangling[0]["line"] == 1, dangling
    findings, _ = lint("```text\n- code and\n```")
    assert not any(f["rule"] == "dangling-conjunction" for f in findings)

    # one- and three-space markers and ordered continuation width
    findings, _ = lint(" - Start the task and\n   record the result.")
    assert not any(f["rule"] == "dangling-conjunction" for f in findings)
    findings, _ = lint("-  Start the task and\n   record the result.")
    assert not any(f["rule"] == "dangling-conjunction" for f in findings)
    findings, _ = lint("-\tStart the task and")
    assert not any(f["rule"] == "dangling-conjunction" for f in findings)
    findings, _ = lint("   - Start the task and", filename="fixture.md")
    dangling = [f for f in findings if f["rule"] == "dangling-conjunction"]
    assert len(dangling) == 1 and dangling[0]["col"] == 4, dangling
    assert dangling[0]["file"] == "fixture.md"
    assert dangling[0]["match"].endswith("and")
    assert "Complete the item" in dangling[0]["message"]
    findings, _ = lint("100. Start the task and\n  unrelated text")
    dangling = [f for f in findings if f["rule"] == "dangling-conjunction"]
    assert len(dangling) == 1, dangling
    findings, _ = lint("- Start the task and.\n- Stop the task or,")
    assert not any(f["rule"] == "dangling-conjunction" for f in findings)
    findings, _ = lint("- Start the task and\n\n  record the result.")
    assert not any(f["rule"] == "dangling-conjunction" for f in findings)
    findings, _ = lint("- Parent item and\n  - Nested item or")
    dangling = [f for f in findings if f["rule"] == "dangling-conjunction"]
    assert [f["line"] for f in dangling] == [1, 2], dangling

    # ordinary prose, inline code, and fenced code are ignored
    findings, _ = lint("The process may include steps and")
    assert not any(f["rule"] == "dangling-conjunction" for f in findings)
    findings, _ = lint("- Use `and` as a label")
    assert not any(f["rule"] == "dangling-conjunction" for f in findings)
    findings, _ = lint("- Combine `left` and `right`")
    assert not any(f["rule"] == "dangling-conjunction" for f in findings), findings
    findings, _ = lint("~~~\n- code and\n~~~")
    assert not any(f["rule"] == "dangling-conjunction" for f in findings)
    findings, _ = lint(("word " * 30).strip() + ".")
    assert any(f["rule"] == "long-sentence" for f in findings)
    # Markdown table syntax is layout, not prose. Each cell stays lintable.
    short_cell = " ".join(f"term{number}" for number in range(1, 25)) + "."
    for table in (
            "| Label | Detail |\n"
            "| --- | --- |\n"
            f"| Clear | {short_cell} |",
            "Label | Detail\n"
            "--- | ---\n"
            f"Clear | {short_cell}"):
        findings, words_total = lint(table)
        assert not any(f["rule"] == "long-sentence" for f in findings), findings
        assert words_total == 27, words_total
    long_cell = " ".join(f"term{number}" for number in range(1, 27)) + "."
    findings, _ = lint(
        "| Label | Detail |\n"
        "| --- | --- |\n"
        f"| Clear | {long_cell} |"
    )
    long_sentences = [f for f in findings if f["rule"] == "long-sentence"]
    assert len(long_sentences) == 1, long_sentences
    assert long_sentences[0]["match"] == "26 words", long_sentences
    # synonym rotation: second member flagged, first named as the keeper
    findings, _ = lint("Check the config file. Then verify the output. Verify twice.")
    rot = [f for f in findings if f["rule"] == "synonym-rotation"]
    assert len(rot) == 1 and "'verify' and 'check'" in rot[0]["message"], rot
    # single consistent term: no flag
    findings, _ = lint("Check the config. Check the output.")
    assert not any(f["rule"] == "synonym-rotation" for f in findings)
    # per-file labels
    findings, _ = lint("a; b", filename="x.md")
    assert findings[0]["file"] == "x.md"

    # ---- Turkish ----
    bad_tr = ("Panel söküldü; servisi ayağa kaldırın. "
              "Kusursuz logun incelemesi gerçekleştirildi. "
              "Çalışma devam etmektedir ve işbu rapor hazırlanmış olup gönderilecektir.")
    rules = _rules(bad_tr)
    for expected in ("semicolon", "phrasal-verb", "nominalization", "marketing-adjective",
                     "passive-voice", "compound-tense", "bureaucratic", "clause-chain"):
        assert expected in rules, expected
    # hedges are content: never flagged
    findings, _ = lint("İstek başarısız olmuş olabilir. Zaman aşımı olabilir. "
                       "Disk muhtemelen doldu. Sanırım sunucu yanıt vermiyor.")
    assert findings == [], findings
    # passive: true positives across tense, negation, ability
    for word in ("gönderildi", "yapılacaktır", "beklenmektedir", "onaylanması", "alınmadı",
                 "silinir", "okunamadı", "edilemez", "yapılabilir", "güncellenmiyor",
                 "İncelendi", "bulunamadı", "atandı", "değerlendirildi"):
        assert "passive-voice" in _rules(f"Rapor dün {word}.", lang="tr"), word
    # passive: stems that only look passive, ability forms, noun + copula
    for word in ("kullandı", "öğrendi", "katıldı", "düşündü", "buldu", "bildi", "yapabilir",
                 "gelebilir", "uygundur", "mümkündür", "değildir", "dahildir", "okuldur",
                 "değerlendirdi", "bilgilendirdi", "yapılandırdı", "bulunmaktadır",
                 "ilgilendi", "yazılımdır", "kurulumu", "Yılmaz", "belirtilen"):
        assert "passive-voice" not in _rules(f"Ekip bunu {word}.", lang="tr"), word
    # ordinal and abbreviation periods do not end a sentence
    assert len(tr_sentences("Dosyayı aç ve 3. satırı oku. Sonra kapat.")) == 2
    assert len(tr_sentences("Log, metrik vb. kayıtları sil.")) == 1
    long_tr = "Ekip " + "kelime " * 18 + "yazdı."
    assert "long-sentence" in _rules(long_tr, lang="tr")
    assert "long-sentence" not in _rules("Ekip " + "kelime " * 16 + "yazdı.", lang="tr")
    # a 20-word Turkish sentence breaks the Turkish cap, not the English one
    assert "long-sentence" not in _rules(long_tr, lang="en")
    # converb chain needs two converbs; noun look-alikes do not count
    assert "clause-chain" in _rules("Dosyayı açıp kontrol ettikten sonra gönder.")
    assert "clause-chain" not in _rules("Dosyayı açıp oku.")
    assert "clause-chain" not in _rules("Ekip takip için backup aldı ve taslak olarak gönderdi.")
    # synonym rotation
    findings, _ = lint("Dosyayı kontrol et. Sonra çıktıyı doğrula.")
    rot = [f for f in findings if f["rule"] == "synonym-rotation"]
    assert len(rot) == 1 and "'doğrula' ve 'kontrol et'" in rot[0]["message"], rot
    assert "synonym-rotation" not in _rules("Dosyayı kontrol et. Çıktıyı kontrol edin.")
    assert "synonym-rotation" not in _rules("Ekleri gönder. Görüntüler ektedir.")
    # dangling conjunction in a Turkish list
    findings, _ = lint("- Hedefi doğrula ve\n- Sonucu kaydet")
    dangling = [f for f in findings if f["rule"] == "dangling-conjunction"]
    assert len(dangling) == 1 and dangling[0]["lang"] == "tr", dangling
    # code is skipped; columns survive inline code
    assert lint("```\nx = a; y = b; // gönderildi\n```")[0] == []
    findings, _ = lint("Şu `a; b` komutu çalıştır; sonra bekle.")
    semis = [f for f in findings if f["rule"] == "semicolon"]
    assert len(semis) == 1 and semis[0]["col"] == 26, semis
    # İ/I casing and NFD input
    assert "passive-voice" in _rules("İPTAL EDİLDİ.", lang="tr")
    assert "bureaucratic" in _rules(unicodedata.normalize("NFD", "İşbu belge geçerlidir."))
    # language detection: per line, English rules stay off Turkish text and vice versa
    assert detect_lang("Rapor gönderildi.") == "tr"
    assert detect_lang("The report was sent.") == "en"
    mixed = lint("Rapor gönderildi.\nThe building is ready.\n")[0]
    assert [f["lang"] for f in mixed] == ["tr"], mixed
    print("selftest OK")


def main(argv):
    for stream in (sys.stdout, sys.stderr, sys.stdin):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    if "--selftest" in argv:
        selftest()
        return 0
    as_json = "--json" in argv
    baseline = 0
    disabled = set()
    lang = "auto"
    allowed = []
    max_words_en, max_words_tr = MAX_WORDS, MAX_WORDS_TR
    paths = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--baseline":
            i += 1
            baseline = int(argv[i])
        elif a == "--disable":
            i += 1
            disabled = set(argv[i].split(","))
        elif a == "--lang":
            i += 1
            lang = argv[i]
            if lang not in ("auto", "tr", "en"):
                print("--lang must be auto, tr or en", file=sys.stderr)
                return 2
        elif a == "--allow":
            i += 1
            allowed = [tr_lower(term.strip()) for term in argv[i].split(",") if term.strip()]
        elif a == "--max-words-en":
            i += 1
            max_words_en = int(argv[i])
        elif a == "--max-words-tr":
            i += 1
            max_words_tr = int(argv[i])
        elif not a.startswith("--"):
            paths.append(a)
        i += 1

    options = {"lang": lang, "max_words_en": max_words_en, "max_words_tr": max_words_tr}
    findings, words_total = [], 0
    if paths:
        for p in paths:
            f, w = lint(open(p, encoding="utf-8-sig").read(), filename=p, **options)
            findings.extend(f)
            words_total += w
    else:
        findings, words_total = lint(sys.stdin.read(), **options)

    findings = [f for f in findings if f["rule"] not in disabled]
    # project glossary: STE lets a project approve its own terms
    findings = [f for f in findings
                if not any(term in " ".join(tr_lower(f["match"]).split()) for term in allowed)]
    hard_count = sum(1 for f in findings if f["level"] == "advisory-free")
    report(findings, words_total, as_json, hard_count, baseline)
    return 1 if hard_count > baseline else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
