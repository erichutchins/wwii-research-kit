import pytest
from wwiibook.cite import parse


def test_morning_report_roll():
    c = parse("rg64-469722323/p0712")
    assert (c.archive, c.group, c.item, c.page) == ("nara", 64, "469722323", 712)
    assert c.link == "https://catalog.archives.gov/id/469722323?objectPage=712"
    assert c.credit == "National Archives, RG 64, NAID 469722323, p. 712"


def test_patrol_report():
    c = parse("rg38-74802746/p16")
    assert (c.group, c.item, c.page) == (38, "74802746", 16)


@pytest.mark.parametrize("bad", ["jacar:C08030140600/p15", "rg64-469722323", "74802746/p16", ""])
def test_unreadable(bad):
    with pytest.raises(ValueError):
        parse(bad)
