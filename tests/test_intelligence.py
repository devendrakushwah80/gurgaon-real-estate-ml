from app.security import create_access_token, decode_access_token, hash_password, verify_password
from app.services import intelligence


def _record(**overrides):
    value = {
        "id": "source-test",
        "title": "3 BHK Apartment",
        "property_type": "flat",
        "bhk": 3,
        "locality": "Sector 57",
        "sector": "Sector 57",
        "city": "Gurgaon",
        "area_sqft": 1500,
        "listing_price": 1.8,
        "property_age": "New Property",
        "furnishing": "semifurnished",
        "description": "Bright apartment",
        "amenities": ["Gym", "Park", "Security"],
        "images": [],
        "source": "99acres",
        "source_url": "https://www.99acres.com/example",
        "model_payload": {},
    }
    value.update(overrides)
    return value


def test_scores_are_explainable_and_independent(monkeypatch):
    monkeypatch.setattr(intelligence, "load_catalog", lambda: (_record(),))
    record = _record()
    valuation = {"listing_price": 1.8, "fair_value": 2.0, "difference_percent": -10.0}
    trust = intelligence.trust_score(record, valuation)
    investment = intelligence.investment_score(record, valuation, trust)
    assert 0 <= trust["score"] <= 100
    assert 0 <= investment["score"] <= 100
    assert "price_consistency" in trust["breakdown"]
    assert "valuation_advantage" in investment["breakdown"]
    assert trust["score"] != investment["score"] or trust["breakdown"] != investment["breakdown"]
    assert any("image" in warning.lower() for warning in trust["warnings"])


def test_passwords_and_access_tokens_are_verifiable():
    encoded = hash_password("EstateIQ123")
    assert encoded != "EstateIQ123"
    assert verify_password("EstateIQ123", encoded)
    assert not verify_password("wrong", encoded)
    token = create_access_token(7, "user@example.com", ["USER"])
    claims = decode_access_token(token)
    assert claims["sub"] == "7"
    assert claims["roles"] == ["USER"]
