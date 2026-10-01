from app.services import market_insights, property_catalog


def test_market_insights_are_city_scoped_and_deduplicated(monkeypatch):
    records = [
        {
            "id": "one",
            "source_listing_id": "I-1",
            "city": "indore",
            "locality": "Vijay Nagar",
            "price_per_sqft": 8_000,
            "listing_price": 1.2,
            "area_sqft": 1_500,
        },
        {
            "id": "duplicate",
            "source_listing_id": "I-1",
            "city": "indore",
            "locality": "Vijay Nagar",
            "price_per_sqft": 99_000,
            "listing_price": 9,
            "area_sqft": 1_500,
        },
        {
            "id": "two",
            "source_listing_id": "I-2",
            "city": "indore",
            "locality": "Super Corridor",
            "price_per_sqft": None,
            "listing_price": 0.9,
            "area_sqft": 1_000,
        },
    ]

    def fake_search_catalog(**filters):
        assert filters == {"city": "indore"}
        return records

    monkeypatch.setattr(market_insights, "search_catalog", fake_search_catalog)
    result = market_insights.build_market_insights("Indore")

    assert result["city"] == "indore"
    assert result["summary"]["listing_count"] == 2
    assert result["summary"]["locality_count"] == 2
    assert {item["median_price_per_sqft"] for item in result["localities"]} == {8_000, 9_000}


def test_catalog_location_area_and_property_type_filters(monkeypatch):
    records = (
        {
            "id": "one",
            "city": "indore",
            "locality": "Vijay Nagar",
            "sector": None,
            "project_name": "Skyline",
            "title": "Apartment in Indore",
            "area_sqft": 1_250,
            "property_type": "Residential Apartment",
        },
        {
            "id": "two",
            "city": "indore",
            "locality": "Super Corridor",
            "sector": None,
            "project_name": "Green Plot",
            "title": "Land in Indore",
            "area_sqft": 2_500,
            "property_type": "Residential Land",
        },
        {
            "id": "three",
            "city": "gurgaon",
            "locality": "Vijay Vihar",
            "area_sqft": 1_250,
            "property_type": "flat",
        },
    )
    monkeypatch.setattr(property_catalog, "load_catalog", lambda: records)

    matches = property_catalog.search_catalog(
        city="indore",
        locality="sky",
        min_area_sqft=1_000,
        max_area_sqft=1_500,
        property_type="apartment",
    )

    assert [item["id"] for item in matches] == ["one"]
