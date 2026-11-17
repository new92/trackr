from trackr.i18n import LABELS, SUPPORTED, language_or_none, legacy_labels
from trackr.translation import translate_dynamic


def test_all_locales_have_same_ui_keys():
    keys = set(LABELS["en"])
    assert set(SUPPORTED) == set(LABELS)
    for value in LABELS.values():
        assert set(value) == keys
        assert all(isinstance(s, str) and s for s in value.values())


def test_language_whitelist_and_legacy_api():
    assert language_or_none("es") == "es"
    assert language_or_none("../../etc/passwd") is None
    assert legacy_labels("el")["station"] == "Σταθμός"
    assert "true" in legacy_labels("en")


def test_optional_machine_translation_off_returns_greek_original():
    text = "Δοκιμαστική ανακοίνωση"
    assert translate_dynamic(text, "fr", enabled=False) == text
    assert translate_dynamic(text, "el", enabled=True) == text
