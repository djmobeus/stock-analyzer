"""Tests for Interactive Investor CSV import."""

from data.ii_import import normalise_epic, parse_ii_csv


def test_normalise_epic():
    assert normalise_epic("AAF") == "AAF.L"
    assert normalise_epic("PRU.L") == "PRU.L"


def test_parse_ii_csv_basic():
    csv_text = """Symbol,Name,Quantity,Average Price
AAF,Airtel Africa,100,350.5
PRU,Prudential,50,1200
"""
    rows = parse_ii_csv(csv_text)
    assert len(rows) == 2
    assert rows[0].ticker == "AAF.L"
    assert rows[0].quantity == 100.0


def test_parse_ii_csv_ii_export_with_bom():
    """Interactive Investor export: Qty, multiple BOM on Symbol."""
    csv_text = (
        "\ufeff\ufeffSymbol,Name,Qty,Price,Average Price,Book Cost\n"
        "AAF,Airtel Africa,100,3.50,350.5,35000\n"
    )
    rows = parse_ii_csv(csv_text)
    assert len(rows) == 1
    assert rows[0].ticker == "AAF.L"
    assert rows[0].quantity == 100.0
