from enrichment import matching


def test_company_matches_rejects_other_company():
    headline = "Growth @ KugelAudio (YC P26)"
    assert not matching.company_matches(headline, "telli.com", ["telli"])
    assert matching.company_matches(headline, "kugelaudio.com", [])


def test_company_matches_by_name_with_legal_suffix():
    assert matching.company_matches("Head of Product at smao GmbH", "smao.ai", ["smao GmbH"])
    assert matching.company_matches("CTO · Sipgate", None, ["sipgate GmbH"])


def test_name_inside_another_word_is_no_match():
    assert not matching.company_matches("Head of Business Intelligence at Acme", "telli.com", ["telli"])
    assert matching.company_matches("Engineer at Kugel Audio", "kugelaudio.com", [])


def test_short_names_need_word_boundary():
    # "ai" from a domain like ai.com must not match inside every word
    assert not matching.company_matches("Founder at Maintained", "ai.com", [])


def test_free_mail():
    assert matching.is_free_mail("gmail.com")
    assert matching.is_free_mail("GMX.de")
    assert not matching.is_free_mail("telli.com")
    assert not matching.is_free_mail(None)


def test_email_domain():
    assert matching.email_domain("Alberto@KugelAudio.com ") == "kugelaudio.com"
    assert matching.email_domain("no-at-sign") is None
