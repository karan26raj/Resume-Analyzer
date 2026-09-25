"""Grounding checks used by analysis (phase 13) and resume rewriting (phase 12)."""
import pytest

from app.services.evidence import is_supported, salient_terms, unsupported_terms


RESUME = """Alex Rivera - Backend Engineer
Built REST APIs in Python with FastAPI and PostgreSQL.
Added Redis caching that cut p95 latency by 40%.
Deployed services with Docker and CI/CD on GitHub Actions.
Worked with Node.js and C++ at Northwind Labs."""


@pytest.mark.parametrize(
    "quote",
    [
        "Built REST APIs in Python with FastAPI and PostgreSQL.",
        "built rest apis in python   with fastapi",               # case / whitespace
        "Added Redis caching that cut p95 latency by 40 %",       # small formatting difference
        "Built REST APIs in Python using FastAPI and PostgreSQL",  # one word paraphrased
    ],
)
def test_supported_quotes(quote):
    assert is_supported(quote, RESUME)


@pytest.mark.parametrize(
    "quote",
    [
        "",
        "Managed Kubernetes clusters on AWS",
        "Led a team of 12 engineers at Google",
    ],
)
def test_unsupported_quotes(quote):
    assert not is_supported(quote, RESUME)


def test_salient_terms_detects_technologies_numbers_and_names():
    terms = salient_terms("Developed APIs using FastAPI, Kubernetes and C++, cutting cost by 30% at Acme.")

    assert terms == ["APIs", "FastAPI", "Kubernetes", "C++", "30", "Acme"]


def test_sentence_initial_words_are_not_salient():
    assert salient_terms("Developed services. Improved latency.") == []


def test_unsupported_terms_allows_rephrasing_of_existing_content():
    rewritten = "Developed RESTful APIs in Python and FastAPI backed by PostgreSQL, cutting p95 latency by 40%."

    assert unsupported_terms(rewritten, RESUME) == []


def test_unsupported_terms_flags_invented_technologies_and_metrics():
    rewritten = "Architected Kubernetes microservices on AWS serving 10M users with Docker."

    assert unsupported_terms(rewritten, RESUME) == ["Kubernetes", "AWS", "10M"]


def test_terms_must_match_whole_words():
    # "95" appears only inside "p95", and "Java" only inside "JavaScript": both count as invented.
    assert unsupported_terms("Reached 95% coverage in Java.", RESUME) == ["95", "Java"]
    assert unsupported_terms("Reached 95% coverage in Java.", RESUME + " JavaScript") == ["95", "Java"]


def test_unsupported_terms_handles_punctuated_technologies():
    assert unsupported_terms("Used Node.js, C++ and CI/CD pipelines.", RESUME) == []
    assert unsupported_terms("Used C# and Vue.js.", RESUME) == ["C#", "Vue.js"]
