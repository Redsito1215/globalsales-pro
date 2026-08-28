from shared.roles_registry import PAGE_CATALOG, SECTION_LABELS


def test_information_levels_are_consistent():
    assert SECTION_LABELS["ops"] == "Operativo"
    assert SECTION_LABELS["gestion"] == "Táctico"
    assert SECTION_LABELS["q2"] == "Estratégico"

    assert PAGE_CATALOG["ventas"]["section"] == "ops"
    assert PAGE_CATALOG["reportes"]["section"] == "gestion"
    assert PAGE_CATALOG["orders"]["section"] == "gestion"
    assert PAGE_CATALOG["dashboard"]["section"] == "q2"
    assert PAGE_CATALOG["reportes-compuestos"]["section"] == "q2"
