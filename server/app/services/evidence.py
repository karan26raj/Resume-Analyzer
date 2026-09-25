import re

_WORD = re.compile(r"[a-z0-9]+")
_TERM = re.compile(r"[A-Za-z0-9][A-Za-z0-9+#./-]*")
_SENTENCE_END = re.compile(r"[.!?:;\n•\-–—*]\s*$")

_SUFFIXES = ("ful", "ing", "ed", "es", "s")


def normalize(text: str) -> str:
    text = text.lower()
    text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    text = re.sub(r"[‐-―]", "-", text)
    return re.sub(r"\s+", " ", text).strip()


def words(text: str) -> list[str]:
    return _WORD.findall(normalize(text))


def is_supported(quote: str, source_text: str, min_overlap: float = 0.8) -> bool:
    quote_norm = normalize(quote or "")
    if not quote_norm:
        return False
    source_norm = normalize(source_text or "")
    if quote_norm in source_norm:
        return True

    quote_words = [word for word in words(quote_norm) if len(word) > 1]
    if not quote_words:
        return False
    source_words = set(words(source_norm))
    found = sum(1 for word in quote_words if word in source_words)
    return found / len(quote_words) >= min_overlap


def _stem(word: str) -> str:
    for suffix in _SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 2:
            return word[: -len(suffix)]
    return word


def _is_salient(token: str, sentence_start: bool) -> bool:
    if any(char.isdigit() for char in token):
        return True
    if any(char in "+#./" for char in token.strip(".")):
        return True
    if len(token) >= 2 and token.isupper():
        return True
    if any(char.isupper() for char in token[1:]):
        return True
    return token[0].isupper() and not sentence_start


def salient_terms(text: str) -> list[str]:
    terms = []
    for match in _TERM.finditer(text or ""):
        token = match.group().rstrip(".-/")
        if not token:
            continue
        before = text[: match.start()]
        sentence_start = not before.strip() or bool(_SENTENCE_END.search(before))
        if _is_salient(token, sentence_start):
            terms.append(token)
    return terms


def unsupported_terms(candidate: str, source_text: str) -> list[str]:
    source_norm = normalize(source_text or "")
    source_words = set(words(source_norm))
    source_stems = {_stem(word) for word in source_words}

    missing: list[str] = []
    for term in salient_terms(candidate):
        term_norm = normalize(term)
        if re.search(rf"(?<![a-z0-9]){re.escape(term_norm)}(?![a-z0-9])", source_norm):
            continue
        has_symbols = bool(re.search(r"[+#.]", term_norm))
        parts = words(term_norm)
        if not has_symbols and parts and all(part in source_words or _stem(part) in source_stems for part in parts):
            continue
        if term not in missing:
            missing.append(term)
    return missing


def canonical_term(term: str) -> str:
    canonical = re.sub(r"[^a-z0-9+#]", "", normalize(term))
    if canonical.endswith("js") and len(canonical) > 4:
        canonical = canonical[:-2]
    return canonical


def mentions(term: str, text: str) -> bool:
    term_norm = normalize(term or "")
    text_norm = normalize(text or "")
    if not term_norm or not text_norm:
        return False

    if re.search(rf"(?<![a-z0-9]){re.escape(term_norm)}(?![a-z0-9])", text_norm):
        return True

    canonical = canonical_term(term_norm)
    if canonical and canonical in {canonical_term(token) for token in _TERM.findall(text_norm)}:
        return True

    if re.search(r"[+#]", term_norm):
        return False
    parts = [part for part in words(term_norm) if len(part) > 1]
    if not parts:
        return False
    text_words = set(words(text_norm))
    text_stems = {_stem(word) for word in text_words}
    return all(part in text_words or _stem(part) in text_stems for part in parts)
