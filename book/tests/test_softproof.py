"""Soft-proofing's colour arithmetic: CIEDE2000 against Sharma, Wu and Dalal's published test pairs, and a proof
through sRGB itself (a press that prints exactly what the screen shows) changing nothing."""
import pytest
from PIL import ImageCms
from wwiibook import softproof as sp

# (L*a*b* 1, L*a*b* 2, ΔE00) from Sharma, Wu and Dalal (2005), Table 1, pairs 1, 7, 17, 25
SHARMA = [
    ((50.0, 2.6772, -79.7751), (50.0, 0.0, -82.7485), 2.0425),
    ((50.0, 0.0, 0.0), (50.0, -1.0, 2.0), 2.3669),
    ((50.0, 2.5, 0.0), (73.0, 25.0, -18.0), 27.1492),
    ((60.2574, -34.0099, 36.2677), (60.4626, -34.1751, 39.4387), 1.2644),
]


@pytest.mark.parametrize("l1,l2,want", SHARMA)
def test_ciede2000(l1, l2, want):
    assert sp.de2000(l1, l2) == pytest.approx(want, abs=1e-4)


def test_lab_of_black_white_and_the_hit_red():
    assert sp.lab("#000000")[0] == pytest.approx(0, abs=0.01)
    assert sp.lab("#ffffff")[0] == pytest.approx(100, abs=0.01)
    L, a, _ = sp.lab("#c8323c")
    assert 40 < L < 50 and a > 50                # a strong mid red


def test_proofing_through_srgb_changes_nothing(tmp_path):
    icc = tmp_path / "srgb.icc"
    icc.write_bytes(ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes())
    for r in sp.palette(icc):
        assert r["shift"] < 1.0, r
    close = [p for p in sp.pairs(icc) if p["print"] < 15]
    assert not close, close                      # the signals are apart on screen
