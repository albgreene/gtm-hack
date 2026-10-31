from enrichment.sources import hubspot

OWNERS = {"87298322": "Kajo Kratzenstein"}


def test_open_deal_sets_owner():
    deals = [{"pipeline": "default", "dealstage": "5816305880", "hubspot_owner_id": "87298322"}]
    flags = hubspot.crm_flags("opportunity", deals, OWNERS)
    assert flags == {"is_customer": False, "is_investor": False, "open_deal_owner": "Kajo Kratzenstein",
                     "lifecycle_stage": "Opportunity", "do_not_contact": False}


def test_closed_won_or_production_is_customer():
    for stage in ("closedwon", "5818079442", "6157013239", "6163434745"):
        flags = hubspot.crm_flags("lead", [{"pipeline": "default", "dealstage": stage}], OWNERS)
        assert flags["is_customer"], stage
        assert flags["open_deal_owner"] is None


def test_customer_lifecycle_is_customer():
    assert hubspot.crm_flags("customer", [], OWNERS)["is_customer"]


def test_investor_by_lifecycle_or_fundraising_deal():
    assert hubspot.crm_flags("6144324828", [], OWNERS)["is_investor"]
    committed = [{"pipeline": "4055645375", "dealstage": "5898277080"}]
    assert hubspot.crm_flags(None, committed, OWNERS)["is_investor"]
    declined = [{"pipeline": "4055645375", "dealstage": "5898277081"}]
    assert not hubspot.crm_flags(None, declined, OWNERS)["is_investor"]


def test_no_sales_contact_lifecycle():
    flags = hubspot.crm_flags("6157284596", [], OWNERS)
    assert flags["do_not_contact"]
    assert flags["lifecycle_stage"] == "Kein Vertriebskontakt"


def test_closed_lost_is_nothing():
    flags = hubspot.crm_flags("lead", [{"pipeline": "default", "dealstage": "closedlost"}], OWNERS)
    assert not flags["is_customer"] and flags["open_deal_owner"] is None
