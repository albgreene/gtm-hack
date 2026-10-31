import pytest

from enrichment.sources import needle


def test_voice_engineering_job_beats_founding_marketing():
    titles = ["Founding Marketing Lead", "Internship - Strategy & BizOps", "Engineering, Voice AI",
              "Workplace and People Operations Manager", "Senior Backend Engineer"]
    ranked = sorted(titles, key=lambda t: -needle.job_score(t))
    assert ranked[0] == "Engineering, Voice AI"
    assert ranked[1] == "Senior Backend Engineer"
    assert needle.job_score("Founding Marketing Lead") == 0


def test_write_tools_are_refused(monkeypatch):
    monkeypatch.setenv("NEEDLE_API_KEY", "x")
    with pytest.raises(PermissionError):
        needle._call("needleSendLinkedinMessage", {"text": "hi"})
