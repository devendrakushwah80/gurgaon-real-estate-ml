from src.data.preprocessing import treat_price
from src.features.engineering import categorize_age_possession, convert_to_sqft
from src.features.selection import categorize_floor, categorize_luxury


def test_treat_price_converts_lac_to_crore():
    assert treat_price("85 Lac") == 0.85


def test_treat_price_converts_crore():
    assert treat_price("1.25 Cr") == 1.25


def test_convert_to_sqft_handles_square_yards():
    assert convert_to_sqft("100 sq. yard") == 900


def test_category_helpers():
    assert categorize_age_possession("1 to 5 Year Old") == "Relatively New"
    assert categorize_luxury(75) == "Medium"
    assert categorize_floor(12) == "High Floor"

