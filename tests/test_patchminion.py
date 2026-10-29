"""Tests for PatchMinion's non-model logic (parsing, fallback, report).

These run with no OpenMinion install and no credentials:
    python -m pytest tests/ -q
"""

import json

import pytest

from patchminion.fallback import classify_issue
from patchminion.models import Issue, Triage, load_issues
from patchminion.parsing import extract_json_object, parse_triage
from patchminion.report import fixture_fingerprint, render_markdown

GOOD_REPLY = """Here is the triage you asked for:
{"triage": [{"issue_number": 7, "category": "bug", "labels": ["bug", "crash"],
"priority": "P1", "summary": "Crashes on launch.", "first_response": "Thanks!"}]}
Hope that helps!"""


def test_extract_json_object_skips_prose_and_nested_braces():
    obj = extract_json_object('pre {"a": {"b": "}"}, "c": 1} post')
    assert obj == {"a": {"b": "}"}, "c": 1}


def test_extract_json_object_rejects_garbage():
    with pytest.raises(ValueError):
        extract_json_object("no json here")
    with pytest.raises(ValueError):
        extract_json_object('{"unterminated": ')


def test_parse_triage_happy_path():
    triage = parse_triage(GOOD_REPLY, 7)
    assert triage.category == "bug"
    assert triage.priority == "P1"
    assert triage.labels == ["bug", "crash"]
    assert triage.source == "model"


def test_parse_triage_adds_category_label_for_feature():
    reply = ('{"triage": [{"issue_number": 3, "category": "feature", '
             '"labels": ["api"], "priority": "P2", "summary": "s", '
             '"first_response": "f"}]}')
    triage = parse_triage(reply, 3)
    assert triage.labels[0] == "enhancement"


def test_parse_triage_rejects_unknown_label_and_category():
    bad_label = ('{"triage": [{"issue_number": 1, "category": "bug", '
                 '"labels": ["wontfix"], "priority": "P1", "summary": "s", '
                 '"first_response": "f"}]}')
    with pytest.raises(ValueError):
        parse_triage(bad_label, 1)
    bad_cat = ('{"triage": [{"issue_number": 1, "category": "spam", '
               '"labels": ["bug"], "priority": "P1", "summary": "s", '
               '"first_response": "f"}]}')
    with pytest.raises(ValueError):
        parse_triage(bad_cat, 1)


def test_parse_triage_missing_issue():
    with pytest.raises(ValueError):
        parse_triage(GOOD_REPLY, 99)


def test_parse_triage_bare_object_without_issue_number():
    # A single-issue turn's bare verdict is that issue's verdict; every
    # field is still validated.
    reply = ('{"category": "bug", "labels": ["bug", "crash"], '
             '"priority": "P1", "summary": "s", "first_response": "f"}')
    triage = parse_triage(reply, 101)
    assert triage.issue_number == 101
    assert triage.category == "bug"
    assert triage.priority == "P1"


def test_parse_triage_accepts_issues_wrapper():
    reply = ('{"issues": [{"issue_number": 105, "category": "bug", '
             '"labels": ["bug", "performance"], "priority": "P2", '
             '"summary": "s", "first_response": "f"}]}')
    triage = parse_triage(reply, 105)
    assert triage.issue_number == 105
    assert triage.labels == ["bug", "performance"]


def test_parse_triage_rejects_mismatched_issue_number():
    reply = ('{"issue_number": 5, "category": "bug", "labels": ["bug"], '
             '"priority": "P1", "summary": "s", "first_response": "f"}')
    with pytest.raises(ValueError):
        parse_triage(reply, 7)


def test_parse_triage_does_not_duplicate_category_label():
    reply = ('{"triage": [{"issue_number": 2, "category": "feature", '
             '"labels": ["enhancement", "ui"], "priority": "P3", '
             '"summary": "s", "first_response": "f"}]}')
    triage = parse_triage(reply, 2)
    assert triage.labels == ["enhancement", "ui"]


def test_parse_triage_rejects_natural_language_priority():
    # The gate stays strict: "high" is not P1, "critical" is not P0.
    reply = ('{"triage": [{"issue_number": 1, "category": "bug", '
             '"labels": ["bug"], "priority": "high", "summary": "s", '
             '"first_response": "f"}]}')
    with pytest.raises(ValueError):
        parse_triage(reply, 1)


@pytest.mark.parametrize(
    "title,body,category,priority",
    [
        ("App crashes on startup", "Stack trace attached, regression since v2", "bug", "P1"),
        ("Add support for dark mode", "Feature request, would be nice", "feature", "P2"),
        ("How do I reset my password?", "Is it possible from the API?", "question", "P2"),
        ("Typo in README", "Documentation fix", "docs", "P3"),
        ("Bump dependencies", "Upgrade CI and deprecate old config", "chore", "P2"),
        ("Passwords stored in plaintext", "Security vulnerability, data loss risk", "bug", "P0"),
    ],
)
def test_fallback_classification(title, body, category, priority):
    triage = classify_issue(Issue(number=1, title=title, body=body))
    assert triage.category == category
    assert triage.priority == priority
    assert triage.source == "fallback"
    assert triage.validate() == []


def test_fallback_is_deterministic():
    issue = Issue(number=5, title="Intermittent failure", body="Sometimes fails randomly")
    assert classify_issue(issue).to_dict() == classify_issue(issue).to_dict()


def test_load_issues_and_fingerprint(tmp_path):
    fixture = tmp_path / "issues.json"
    fixture.write_text(json.dumps([
        {"number": 1, "title": "A", "body": "b", "labels": ["x"]},
        {"number": 2, "title": "B"},
    ]))
    issues = load_issues(fixture)
    assert [i.number for i in issues] == [1, 2]
    assert issues[1].body == ""
    assert fixture_fingerprint(issues) == fixture_fingerprint(list(issues))
    assert len(fixture_fingerprint(issues)) == 12


def test_load_issues_rejects_duplicates(tmp_path):
    fixture = tmp_path / "dup.json"
    fixture.write_text(json.dumps([
        {"number": 1, "title": "A"}, {"number": 1, "title": "B"},
    ]))
    with pytest.raises(ValueError):
        load_issues(fixture)


def test_triage_validate_catches_bad_values():
    bad = Triage(issue_number=1, category="nope", priority="P9", labels=["zzz"])
    problems = bad.validate()
    assert len(problems) == 3


def test_effective_mode_requires_a_real_model_verdict():
    from patchminion.cli import effective_mode

    stub = classify_issue(Issue(number=1, title="Bug", body="it crashes"))
    model = parse_triage(GOOD_REPLY, 7)
    assert effective_mode([stub]) == "stub"
    assert effective_mode([stub, model]) == "model"
    assert effective_mode([]) == "stub"


def test_render_markdown_labels_stub_mode():
    issues = [Issue(number=1, title="Bug | with pipe", body="it crashes")]
    verdicts = [classify_issue(issues[0])]
    md = render_markdown(issues, verdicts, mode="stub", log=["line"])
    assert "NOT a model run" in md
    assert "Bug \\| with pipe" in md
    assert "Verdicts from the model: 0/1" in md
