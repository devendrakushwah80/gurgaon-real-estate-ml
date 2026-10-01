from app.services.property_catalog import search_catalog
from src.ingestion.apify99acres import Apify99AcresAdapter, normalize_apify_items
from src.ingestion.base import FetchResult, RawListing
from src.ingestion.deduplication import deduplicate
from src.ingestion.freshness import ListingStatus, classify_fetch
from src.ingestion.image_extractor import extract_exact_image
from src.ingestion.normalizer import normalize_city
from src.ingestion.parse99acres import Parse99AcresAdapter, normalize_response
from src.ingestion.search_parser import parse_detail_page, parse_search_page


def test_city_aliases_are_canonical_and_distinct():
    assert normalize_city("Gurugram") == "gurgaon"
    assert normalize_city("Indore") == "indore"
    assert normalize_city("Gurgaon") != normalize_city("Indore")


def test_freshness_does_not_call_blocked_pages_active():
    status, reason = classify_fetch(http_status=403, blocked=True)
    assert status == ListingStatus.UNREACHABLE
    assert "blocked" in reason.lower()


def test_image_requires_exact_page_evidence():
    html = '<meta property="og:image" content="https://cdn.example.test/one.jpg">'
    image = extract_exact_image(html, listing_url="https://www.99acres.com/listing/1")
    assert image is not None
    assert image.match_confidence == 1.0
    assert (
        extract_exact_image("<html></html>", listing_url="https://www.99acres.com/listing/1")
        is None
    )


def test_deduplication_prefers_source_id_within_city():
    records = [
        {"id": "one", "source": "99acres", "city": "gurgaon", "source_listing_id": "abc"},
        {"id": "two", "source": "99acres", "city": "gurgaon", "source_listing_id": "abc"},
        {"id": "three", "source": "99acres", "city": "indore", "source_listing_id": "abc"},
    ]
    unique, duplicates = deduplicate(records)
    assert [item["id"] for item in unique] == ["one", "three"]
    assert len(duplicates) == 1


def test_search_parser_extracts_multiple_exact_cards_not_search_page():
    html = """
    <html><head><title>Indore properties</title></head><body>
      <article><a href="/2-bhk-flat-vijay-nagar-spid-A100">2 BHK Flat</a><span>₹45 Lac 1100 sqft</span></article>
      <article><a href="https://www.99acres.com/3-bhk-house-scheme-140-spid-A200">3 BHK House</a><span>₹1.2 Cr 1800 sqft</span></article>
      <a href="/property-in-indore-ffid?page=2">Next page</a>
    </body></html>
    """
    parsed = parse_search_page(
        html, page_url="https://www.99acres.com/property-in-indore-ffid?page=1", city="indore"
    )
    assert parsed.candidate_cards == 2
    assert [item.source_listing_id for item in parsed.listings] == ["A100", "A200"]
    assert all("ffid" not in item.source_url for item in parsed.listings)
    assert parsed.listings[0].fields["bhk"] == 2
    assert parsed.listings[0].fields["area_sqft"] == 1100


def test_detail_parser_extracts_structured_fields_and_images():
    html = """
    <meta property="og:title" content="2 BHK Home">
    <script type="application/ld+json">
      {"@type":"Product","name":"2 BHK Home","image":["https://cdn.example.test/a.jpg","https://cdn.example.test/b.jpg"],"offers":{"price":"55"}}
    </script>
    <div>2 BHK · 1200 sqft · ₹55 Lac · Vijay Nagar</div>
    """
    listing = parse_detail_page(
        html, detail_url="https://www.99acres.com/2-bhk-home-spid-Z900", city="indore"
    )
    assert listing is not None
    assert listing.source_listing_id == "Z900"
    assert listing.fields["bhk"] == 2
    assert len(listing.images) == 2
    assert listing.source_url.endswith("spid-Z900")


def test_empty_search_page_has_no_fake_listing():
    parsed = parse_search_page(
        "<html><body>No results</body></html>",
        page_url="https://www.99acres.com/property-in-indore-ffid?page=1",
        city="indore",
    )
    assert parsed.listings == []
    assert parsed.candidate_cards == 0


def test_parse_response_normalizes_documented_fields_and_gallery():
    payload = {
        "data": {
            "current_page": "1",
            "total_count": 1,
            "properties": [
                {
                    "property_id": "I123",
                    "property_name": "2 BHK in Vijay Nagar",
                    "price": "55 Lac",
                    "area": "1200 sqft",
                    "bedrooms": "2",
                    "locality": "Vijay Nagar, Indore",
                    "city": "Indore",
                    "property_type": "Apartment",
                    "details_url": "https://www.99acres.com/2-bhk-vijay-nagar-spid-I123",
                    "images": [
                        "https://cdn.example.test/i1.jpg",
                        {"url": "https://cdn.example.test/i2.jpg"},
                    ],
                    "posted_date": "19th May, 2026",
                    "seller_name": "Example Seller",
                    "is_verified": True,
                    "location_coordinates": {"LATITUDE": "22.7", "LONGITUDE": "75.8"},
                    "amenities": "5,23",
                }
            ],
        },
        "status": "success",
    }
    listings, errors = normalize_response(payload, requested_city="indore")
    assert errors == []
    listing = listings[0]
    assert listing.source_listing_id == "I123"
    assert listing.source_url.endswith("spid-I123")
    assert listing.fields["listing_price"] == 0.55
    assert listing.fields["price_per_sqft"] == 4583.33
    assert listing.fields["latitude"] == 22.7
    assert len(listing.images) == 2


def test_parse_response_handles_short_lakh_price_suffix():
    payload = {
        "data": {
            "properties": [
                {
                    "property_id": "I124",
                    "property_name": "Plot",
                    "price": "45.6 L",
                    "area": "1200 sqft",
                    "city": "Indore",
                    "details_url": "https://www.99acres.com/plot-spid-I124",
                }
            ]
        }
    }
    listings, errors = normalize_response(payload, requested_city="indore")
    assert errors == []
    assert listings[0].fields["listing_price"] == 0.456


def test_parse_response_handles_price_range_unit_after_separator():
    payload = {
        "data": {
            "properties": [
                {
                    "property_id": "I125",
                    "property_name": "Apartment",
                    "price": "1.01 - 1.34 Cr",
                    "area": "1680 sqft",
                    "city": "Indore",
                    "details_url": "https://www.99acres.com/apartment-spid-I125",
                }
            ]
        }
    }
    listings, errors = normalize_response(payload, requested_city="indore")
    assert errors == []
    assert listings[0].fields["listing_price"] == 1.01


def test_parse_response_rejects_malformed_and_cross_city_records():
    payload = {
        "data": {
            "properties": [
                {"property_id": "bad", "city": "Indore"},
                {
                    "property_id": "wrong",
                    "city": "Gurgaon",
                    "details_url": "https://www.99acres.com/a-spid-wrong",
                },
            ]
        }
    }
    listings, errors = normalize_response(payload, requested_city="indore")
    assert listings == []
    assert len(errors) == 2


def test_parse_adapter_uses_page_pagination_and_handles_mocked_response(monkeypatch):
    payload = {
        "data": {
            "current_page": "2",
            "total_count": 1,
            "properties": [
                {
                    "property_id": "G1",
                    "city": "Gurgaon",
                    "property_name": "Home",
                    "details_url": "https://www.99acres.com/home-spid-G1",
                }
            ],
        },
        "status": "success",
    }

    class Response:
        status = 200

        def geturl(self):
            return "https://api.parse.bot/response"

        def read(self):
            return __import__("json").dumps(payload).encode()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["key"] = request.headers.get("X-api-key") or request.headers.get("X-API-Key")
        return Response()

    monkeypatch.setattr("src.ingestion.parse99acres.urlopen", fake_urlopen)
    result = Parse99AcresAdapter(api_key="test-key").fetch_search(city="gurgaon", page=2)
    assert "page=2" in captured["url"]
    assert "location=gurgaon" in captured["url"]
    assert captured["key"] == "test-key"
    assert result.valid_listing_count == 1
    assert result.listings[0].source_listing_id == "G1"


def test_parse_adapter_surfaces_api_errors(monkeypatch):
    from urllib.error import HTTPError

    def fake_urlopen(request, timeout):
        raise HTTPError(
            request.full_url,
            429,
            "rate limit",
            {},
            __import__("io").BytesIO(b'{"message":"slow down"}'),
        )

    monkeypatch.setattr("src.ingestion.parse99acres.urlopen", fake_urlopen)
    result = Parse99AcresAdapter(api_key="test-key").fetch_search(city="indore", page=1)
    assert result.http_status == 429
    assert result.api_error and "slow down" in result.api_error
    assert result.blocked is True


def test_parse_run_reports_pages_candidates_duplicates_and_samples(monkeypatch):
    import src.ingestion.run as ingestion_run

    class FakeAdapter:
        def fetch_search(self, *, city, page):
            listing = RawListing(
                source="99acres",
                source_url=f"https://www.99acres.com/home-spid-{page}",
                source_listing_id=f"P{page}",
                city=city,
                title=f"Home {page}",
                fields={"listing_status": "UNKNOWN"},
            )
            return FetchResult(
                requested_url=f"https://api.test/search_properties?page={page}",
                http_status=200,
                final_url=None,
                body="{}",
                listings=[listing],
                candidate_count=1,
                valid_listing_count=1,
                content_hash=f"hash-{page}",
                raw_payload={"data": {"properties": [listing.raw]}},
            )

    monkeypatch.setattr(ingestion_run, "Parse99AcresAdapter", FakeAdapter)
    monkeypatch.setattr(ingestion_run, "_store", lambda records: len(records))
    report = ingestion_run.run("indore", pages=3, provider="parse", debug=False)
    assert report["api_requests"] == 3
    assert report["listing_candidates"] == 3
    assert report["unique_listings"] == 3
    assert report["stored_listings"] == 3
    assert len(report["sample_source_listing_ids"]) == 3


def test_catalog_city_filter_does_not_mix_supported_cities():
    assert all(item.get("city") == "gurgaon" for item in search_catalog(city="gurgaon"))
    assert all(item.get("city") == "indore" for item in search_catalog(city="indore"))


def test_apify_output_normalizes_realistic_actor_fields():
    items = [
        {
            "spid": "I-500",
            "prop_details_url": "2-bhk-flat-vijay-nagar-spid-I-500",
            "prop_heading": "2 BHK Flat in Vijay Nagar, Indore",
            "city_name": "Indore",
            "locality_wo_city": "Vijay Nagar, Indore",
            "bedroom_num": "2",
            "property_type": "Apartment",
            "price": "55 Lac",
            "area": "1200 sq.ft.",
            "property_images": [
                "https://imagecdn.99acres.com/a.jpg",
                "https://imagecdn.99acres.com/b.jpg",
            ],
            "society_name": "Example Residency",
            "class_heading": "Owner",
            "posting_date__u": 1760000000000,
            "location": {"city_name": "Indore"},
            "is_verified": "Y",
        }
    ]
    listings, errors = normalize_apify_items(items, requested_city="indore")
    assert errors == []
    listing = listings[0]
    assert listing.source_listing_id == "I-500"
    assert listing.source_url.endswith("spid-I-500")
    assert listing.fields["listing_price"] == 0.55
    assert listing.fields["price_per_sqft"] == 4583.33
    assert len(listing.images) == 2


def test_apify_adapter_sends_actor_input_and_parses_dataset(monkeypatch):
    payload = [
        {
            "spid": "G-1",
            "prop_details_url": "https://www.99acres.com/home-spid-G-1",
            "prop_heading": "Gurgaon home",
            "city_name": "Gurgaon",
            "price": "1 Cr",
            "area": "1000 sqft",
        }
    ]

    class Response:
        status = 200

        def geturl(self):
            return "https://api.apify.com/v2/response"

        def read(self):
            return __import__("json").dumps(payload).encode()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["auth"] = request.headers.get("Authorization")
        captured["body"] = __import__("json").loads(request.data.decode())
        return Response()

    monkeypatch.setattr("src.ingestion.apify99acres.urlopen", fake_urlopen)
    result = Apify99AcresAdapter(
        api_token="test-token", actor_id="rigelbytes~99acres-scraper"
    ).fetch_search(city="gurgaon", page=2)
    assert "run-sync-get-dataset-items" in captured["url"]
    assert captured["auth"] == "Bearer test-token"
    assert "page=2" in captured["body"]["startUrls"][0]["url"]
    assert result.valid_listing_count == 1
    assert result.listings[0].source_listing_id == "G-1"


def test_apify_adapter_maps_current_camel_case_schema_and_property_filter(monkeypatch):
    payload = [
        {
            "listingId": "I-700",
            "url": "https://www.99acres.com/flat-spid-I-700",
            "title": "3 BHK Flat",
            "city": "Indore",
            "locality": "Vijay Nagar",
            "propertyType": "Residential Apartment",
            "price": 8_000_000,
            "areaValue": 1_000,
            "pricePerSqft": 8_000,
            "totalFloors": 12,
        }
    ]

    class Response:
        status = 201

        def geturl(self):
            return "https://api.apify.com/v2/response"

        def read(self):
            return __import__("json").dumps(payload).encode()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

    captured = {}

    def fake_urlopen(request, timeout):
        captured["body"] = __import__("json").loads(request.data.decode())
        return Response()

    monkeypatch.setenv("APIFY_PROPERTY_TYPES", "apartment,plot")
    monkeypatch.setattr("src.ingestion.apify99acres.urlopen", fake_urlopen)
    result = Apify99AcresAdapter(api_token="test-token").fetch_search(city="indore", page=1)

    assert captured["body"]["propertyTypes"] == ["apartment", "plot"]
    assert result.listings[0].fields["property_type"] == "Residential Apartment"
    assert result.listings[0].fields["price_per_sqft"] == 8_000
    assert result.listings[0].fields["total_floors"] == 12


def test_explicit_provider_selection_overrides_auto_environment(monkeypatch):
    import src.ingestion.run as ingestion_run

    monkeypatch.setenv("PARSE_99ACRES_API_KEY", "parse-key")
    monkeypatch.setenv("APIFY_API_TOKEN", "apify-key")
    assert ingestion_run.resolve_provider("parse") == "parse"
    assert ingestion_run.resolve_provider("apify") == "apify"
    assert ingestion_run.resolve_provider("auto") == "parse"
