"""Tests for Interactive Investor CSV import."""

from pathlib import Path

from data.ii_import import normalise_epic, parse_ii_csv


def test_normalise_epic():
    assert normalise_epic("AAF") == "AAF.L"
    assert normalise_epic("PRU.L") == "PRU.L"
    assert normalise_epic("BT.A") == "BT-A.L"


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


def test_parse_ii_csv_many_boms_as_bytes():
    """Matches real II export: many BOM chars before Symbol."""
    header = ("\ufeff" * 9) + "Symbol,Name,Qty,Price,Day Gain/Loss,Average Price\n"
    body = "PRU,Prudential,50,12.00,0.1,1200\n"
    rows = parse_ii_csv((header + body).encode("utf-8"))
    assert len(rows) == 1
    assert rows[0].ticker == "PRU.L"


def test_parse_ii_activity_csv_nets_buys_and_sells():
    """Real II transaction export: aggregate open positions."""
    path = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "ii_activity_sample.csv"
    if not path.exists():
        csv_text = """Date,Settlement Date,Symbol,Sedol,Quantity,Price,Description,Reference,Debit,Credit,Running Balance
26/06/2026,26/06/2026,EZJ,B7KR2P8,3903,£5.38,3903 EASYJET  Del    5.38 S Date 26/06/26,ref,n/a,"£20,992.65","£21,832.39"
26/06/2026,30/06/2026,BT.A,3091357,5168,£1.92422,5168 BT GROU  Del    1.92 S Date 30/06/26,ref,"£9,998.15",n/a,"£4,834.90"
29/06/2026,01/07/2026,CHG,B45C9X4,1029,£4.82659,1029 CHEG GROU  Del    4.82 S Date 01/07/26,ref,"£4,995.39",n/a,"£4,878.33"
29/06/2026,01/07/2026,SBRY,B019KW7,1602,£3.14781,1602 SAINSBURY  Del    3.14 S Date 01/07/26,ref,n/a,"£5,038.82","£9,873.72"
06/07/2026,08/07/2026,CHG,B45C9X4,1029,£5.70499,1029 CHEG GROU  Del    5.70 S Date 08/07/26,ref,n/a,"£5,866.46","£10,813.56"
07/07/2026,09/07/2026,BT.A,3091357,2634,£1.88657,2634 BT GROU  Del    1.88 S Date 09/07/26,ref,"£4,998.12",n/a,"£5,345.44"
07/07/2026,09/07/2026,JMAT,BZ4BQC7,251,£19.78199,251 JOHN MATT  Del   19.78 S Date 09/07/26,ref,"£4,994.10",n/a,£351.34
30/06/2026,30/06/2026,IMB,0454492,n/a,n/a,Div 165   IMPERIAL BRANDS PLC   GBP0.10,ref,n/a,£68.77,"£4,947.10"
"""
    else:
        csv_text = path.read_text(encoding="utf-8")

    rows = parse_ii_csv(csv_text)
    by_ticker = {r.ticker: r for r in rows}

    assert "CHG.L" not in by_ticker
    assert by_ticker["SBRY.L"].quantity == 1602
    assert by_ticker["EZJ.L"].quantity == 3903
    assert by_ticker["JMAT.L"].quantity == 251
    assert by_ticker["BT-A.L"].quantity == 7802
    assert by_ticker["IMB.L"].quantity == 165
    assert by_ticker["IMB.L"].avg_cost_gbx is None
