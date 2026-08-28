from shared.company_profile import DEFAULT_COMPANY_PROFILE, _normalize


def test_altavia_trade_is_the_default_brand():
    assert DEFAULT_COMPANY_PROFILE["name"] == "Altavia Trade"
    assert DEFAULT_COMPANY_PROFILE["logo_url"] == "/static/img/altavia-trade-logo.png"


def test_legacy_globtrade_profile_is_migrated_on_read():
    profile = _normalize({
        "name": "GLOBTRADE",
        "legal_name": "GLOBTRADE S.A.",
        "logo_url": "/static/img/globtrade-logo.png",
    })
    assert profile["name"] == "Altavia Trade"
    assert profile["legal_name"] == "Altavia Trade"
    assert profile["logo_url"] == "/static/img/altavia-trade-logo.png"
