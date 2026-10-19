# Japanese Navy position codes (地点符号), 1944-45

Japanese aircraft reported enemy positions as four-character codes: 「メキ三ツ」, 「ヤソ3ス」, 「ホヲ0ヲ」. Started 16 Oct 2026
to plot the 6 April 1945 scouting reports against TF 58, the day USS Haynsworth was hit. The decoder is
`tools/jgrid.py`; the letters worked out so far are in `reference/jgrid/keys.csv` and the evidence in
`reference/jgrid/anchors.csv`.

## How the code works

- **Kana 1 is the column and kana 2 is the row of a 20′ × 20′ square.** The squares sit on whole-degree boundaries.
  The war history 戦史叢書 vol. 56 (*海軍捷号作戦 2*), fig. 34, p. 397, draws part of the grid off Samar on
  25 Oct 1944. Columns ヤ, ノ, ウ run 126°00′-126°20′-126°40′-127°00′E. Rows テ, キ, ツ run 13°00′-12°40′-12°20′-12°00′N.
  The figure plots seven reports, and three of them check against bearings and distances given in the text
  (anchors L1-L3). The 901st Air Group's charts bear this out: ホ is 123°40′E for contacts at 22°, 21°30′ and 17°N,
  and レ is 125°00′E at 22°, 20°45′ and 15°N.
- **The letters are scrambled.** Neighbouring columns and rows aren't in iroha or gojūon order (ヤ, ノ, ウ eastward;
  ツ, キ, テ northward), so each key has to be rebuilt letter by letter from anchors. Columns and rows use separate
  alphabets: in the Formosa key コ is both a column (128°40′E) and a row (21°00′N).
- **The key depends on a base point, which is the fifth character.** A May 1942 base air force order ([C13120115200](https://www.jacar.archives.go.jp/das/image/C13120115200),
  p. 2) lists the "base-point letters for the Second Position-Indication Method" (第二地点表示法ニ於ケル基点附字). These
  include ラエ = エ, ツラギ = ツ, トラック = ト, ラボール = ホ, ヤルート = ヤ, 大島 = ヲ, 木更津 = キ, テニアン = テ and
  ミッドウェー = ミ. In Oct 1944 the 901st's signals end in へ when the search's base point (基点) was 鵝鑾鼻 (Garanbi,
  the south cape of Formosa) and in ヤ when it was Manila or Cavite. The two keys letter the same squares differently:
  column ツ is 122°40′E in the へ key and 125°00′E in the ヤ key. The April 1945 reports from Kanoya carry no suffix.
- **The rows may be shared between keys and repeat every 15°.** See "Rows across keys" below. Columns are not shared.
- **The last two characters (a digit and a kana) place the point inside the square.** Not decoded; see "Subdivision"
  below. Without them the code is good to about ±10 nm, which is about as good as the scouts' own navigation.

## April 1945 key (Kyushu-Okinawa, no suffix)

| | Letter | From | Confidence | Evidence |
|---|---|---|---|---|
| column | ス | 129°20′E | probable | 6 Apr: TG 58.3 has to be one of the four groups reported 1130-1420 (anchor O5) |
| column | メ | 129°40′E | good | 21 Apr track chart (O1, O2) |
| column | サ | 130°00′E | good | 21 Apr track chart (O3); サテ "south of Kikai-jima", 11 Apr (O4) |
| column | ケ | 131°20′E | tentative | 7 Apr 0155: a Recon 703 plane's own position at the end of its search line (O6) |
| row | ツ | 27°00′N | good | 21 Apr track chart (O2, O3) |
| row | キ | 27°20′N | good | 21 Apr track chart (O1) |
| row | テ | 27°40′N | probable | the row after ツ, キ, as at Leyte; fits O4 |
| row | ホ, ニ | south of 27°00′N | unplaced | one of them is 26°40′-27°00′N (TG 58.3 on 6 Apr), the other is not yet placed |

The 21 April anchors come from Recon 11's track chart ([C13120384900](https://www.jacar.archives.go.jp/das/image/C13120384900)
p19, with the codes in the signal log on p15). It is a pencil sketch with islands but no graticule, so I located it from
Tokunoshima, Okinoerabu and Kikai, to about ±10′. The three groups straddle the 130°E and 27°20′N lines in the way the
codes say they should. That is the main check on this key so far.

### 6-7 April sortie pages

I tried to repeat the 901st method (code against the flight's own dead reckoning) for 6 April. Neither report can do
it for the daytime contacts on TF 58:

- **Recon 11** (偵察第11飛行隊, Saiun, [C13120384700](https://www.jacar.archives.go.jp/das/image/C13120384700)). Its
  track charts are listed on p37 (行動図, 別紙第一ノ一 to 第一ノ五 for 6 April's two search stages) but aren't in the
  46-page file: pp. 30-36 are more of the 7-11 April log (p34 repeats p30), pp. 37-46 results, losses, strength,
  citations and crew lists. The orders (pp. 3-4) give the search lines from Cape Toi (都井岬), Cape Sata and Nomazaki.
  Lines have dog-legs, and the handwriting of the first-stage legs is too uncertain to dead-reckon contacts to ±10′
  from times alone. Two things are clear:
  - The second-stage order (p4, about 0900) sends 二番線 to the "敵機動部隊" at 「**メム三ス**」 and on to
    「メヘ一タ」. The kana is a clear ム, not ツ. An earlier reading took the 0800 report as メツ三ス, following the 210th Air
    Group's 「メツミス」. Either one of them miscopied or the order means a different square. ム is not a placed row.
  - The results table (p37) has 一段一番索機 at **0905** reporting 「サヌ一ア」, a force without carriers. The ship type
    reads 輸送船 (transports). Row ヌ isn't placed.
- **Recon 703** (偵察第703飛行隊, G4M, [C13120385000](https://www.jacar.archives.go.jp/das/image/C13120385000)) is a
  night unit. Its 5 April sorties were mine-laying (pp. 5-6). On the night of 6-7 April three aircraft flew the dawn
  search for 7 April (七日黎明索敵), on 130°, 171° and 186° lines of 250 nm (table on the track chart, p17; tip time
  changed to 0200, p10). They saw nothing. Its signals (pp. 11-12), however, give three of the crews' **own
  positions** in code, which is better than a contact. The chart (p17) has courses, distances and times for each leg
  but no graticule, and its sketch of the Osumi coast doesn't fit the drawn scale. So I dead-reckoned from Kanoya:
  - O7, 0225, 「サキ三ツ」, radar failed, continuing on the planned route. Only the 186° plane can be near column サ
    then: it reached its tip at 0218 (Kanoya 186° 250 nm) and turned west on a 30 nm leg. Seven minutes along it, it
    was at 27-18N 130-02E, which is in column サ and 2′ south of row キ. Starting from Cape Toi instead puts it 30′ east,
    outside サ. So the lines started from Kanoya, and サ and キ hold.
  - O6, 0155, 「ケツ一ア」, 3コース at the end of its search line. The 171° plane reached its tip at 0200, at Kanoya
    171° 250 nm = 27-17N 131-36E, in row ツ. That puts **ケ at 131-20E** (tentative). It rests on 3コース being the 171°
    line: the 130° plane's dog-leg ends near 28-15N 134-45E, and the 186° tip is 23 minutes too late.
  - O8, 0527, 「ケワ四セ」, 3コース's 0520 position on the way home (second kana ワ or ク). Not placed: the 171° plane
    turned for home at 0210 but landed only at 0600, so its 0520 position can't be dead-reckoned. If it was 90-110 nm
    short of Kanoya, the row would be at 29-30N, where the shared-rows rule predicts ラ or ヲ. ワ (or ク) doesn't match,
    but the position is too loose to count against the rule.

So the 6-7 April pages add one tentative column (ケ) and support サ, キ and ツ. They don't test the 28-30N rows,
and they don't place ホ or ニ.

## October 1944 keys (901st Air Group)

The 901st Air Group's night-search report for 10-28 Oct 1944 ([C13120398700](https://www.jacar.archives.go.jp/das/image/C13120398700))
ends with two charts (pp. 37-38, 別紙 索敵計画) on a printed 1° graticule. Twenty-three coded contacts are drawn on them
as boxed ☒ with code, suffix and date, plus one given in latitude and longitude. pp. 4-27 are the sortie pages:
orders, crew, track sketch, and the signals sent, with times. I read each code off both the chart and the signal where
I could find it. The chart labels misled me four times: ホク, not ホタ; ツヲ, not トリ, under the fold; ム and モ, not
ハ and キ; ノエ三ス, not 三テ.

To measure the boxes I took the PDF's embedded 6617 × 4680 scans and fitted every graticule line separately: the
lines are hand-ruled and lean by about 1°, and the fits leave 1-3 px (0.2-0.5′) of scatter. Each box centre was then
interpolated between the four lines around it. Checks: Garanbi as drawn is 4′ from its true position, the
(ホタ三クへ) box drawn on both charts measures the same to 2.6′, and a box the chart labels "N21°06′ E125°30′" measures
21°02′N 125°32′E. So a box is good to about ±5′, a quarter of a square. Anchors F1-F17 and M1-M6.

### Formosa key (suffix へ, base point 鵝鑾鼻), 10-27 Oct 1944

| | Letter | From | Confidence | Evidence |
|---|---|---|---|---|
| column | テ | 122°00′E | probable | F6 |
| column | キ | 122°20′E | probable | F5 |
| column | ツ | 122°40′E | good | F7 (12 Oct), F17 (27 Oct) |
| column | ヘ | 123°00′E | good | F1, F4; 戦史叢書 vol. 36 ヘリ4セ = Ishigaki 203° 152 nm (S1) |
| column | ホ | 123°40′E | good | F3, F8, F15 (12, 16, 26 Oct) |
| column | ネ | 124°20′E | probable | F12 |
| column | レ | 125°00′E | good | F9, F11, F16 (16, 17, 26 Oct) |
| column | ソ | 126°00′E | probable | F10 |
| column | リ | 127°40′E | tentative | F13; box 2′ inside the edge, and the sortie's signal doesn't seem to match |
| column | ナ | 128°00′E | probable | F14 |
| column | コ | 128°40′E | tentative | F2; see "How far to trust the chart" |
| row | ヨ | 14°40′N | tentative | F16, 5′ outside. ヨ 15°00′ with シ 15°20′ fits as well |
| row | シ | 15°00′N | tentative | F17 |
| row | タ | 17°00′N | probable | F15 |
| row | セ | 18°40′N | tentative | F14, on the 19°00′ line |
| row | マ | 19°20′N | tentative | F13 |
| row | メ | 20°00′N | good | F4, F12 |
| row | ユ | 20°20′N | tentative | F5, 1′ from the line above |
| row | ス | 20°40′N | probable | F11 |
| row | コ | 21°00′N | good | F6, F10 |
| row | ク | 21°20′N | good | F3, F7 |
| row | リ | 22°00′N | good | F8, F9, S1 |
| row | ウ | 23°00′N | probable | F1 |
| row | ヌ | 24°20′N | tentative | F2 |

The letters held from 10 to 27 Oct: ホ, レ and ツ recur ten days apart in the same columns.

### Manila key (suffix ヤ), 24-28 Oct 1944 (`leyte-1944`)

These extend the fig. 34 letters, which are the same key: the chart's ヤ and ノ contacts (M2, M5) fall in fig. 34's
ヤ and ノ columns.

| | Letter | From | Confidence | Evidence |
|---|---|---|---|---|
| column | ム | 124°40′E | probable | M3 |
| column | ツ | 125°00′E | tentative | M6, 1′ from the column's east edge |
| column | モ | 125°40′E | probable | M4 |
| row | エ | 13°00′N | good | M3, M4, M5, next to fig. 34's テ (12°40′) |
| row | イ | 14°00′N | probable | M2 |
| row | ソ | 14°20′N | tentative | L4 alone. The chart's (?ラ二シヤ) box (M1, first kana hidden) sits in the same row |
| row | ヲ | 14°40′ or 15°00′N | unplaced | the chart puts it at 14°40′ (M6); 戦史叢書 p. 122's conversions (L7-L9) put it at 15°00′-15°20′ |

戦史叢書 vol. 56 p. 122's six conversions for 24 Oct (L5-L10) disagree with the chart and with each other by up to a
row or column (ラ, ウ and ヲ all near 15°N; ニ in two columns), so I've used none of them to place letters.

### How far to trust the chart

The chart is the 901st staff's decoding of the signals. I compared it with the flights' own tracks (search line and
distance from the order, times from the sortie page). Most agree, but two are well off:

| Contact | Chart | Flight | |
|---|---|---|---|
| ヘウ三ウへ, F13, 10 Oct 2108 | 23°09′N 123°07′E | 064° line, ~140 nm out by the track sketch: 22°55′N 123°07′E | agrees |
| ホリ三クへ, F18, 16 Oct 0045 | 22°05′N 123°43′E | 085° line: ~22°07′N 123°32′E | agrees |
| ホタ三クへ, F30, 26 Oct 0045 | 17°07′N 123°46′E | box bears 150° from Garanbi; F30's line was 146° or 155° (order and crew table differ) | agrees in bearing |
| コヌ四エへ, F19, 11 Oct 2230-2345 | 24°27′N 128°53′E | 093° line; F19's own 0100 signal says N22°06′ E125°30′ | ~230 nm apart |
| レス四セへ, KEA95, 17 Oct 0235 | 20°45′N 125°11′E | end of 129° 290 nm leg, contact 50 km ahead: ~18°35′N 125°13′E | 2° apart in latitude |
| ノエ三スヤ, KEA95, 25 Oct 0320 | 13°02′N 126°27′E | the track sketch marks the 0325 force "E127° N13°10′" | same row, 20-40′ apart |

So either the staff sometimes decoded wrong or the crews sometimes encoded wrong, and I can't tell which from this
report. Two other details don't add up either. The 11 Oct fix is N22°06′ in F19's signal but "N21°06′" on the chart.
And KEA95's 17 Oct 0345 signal エコ四コへ ("pillar of fire") is not on the chart; its track puts it near 19°55′N, a degree
south of row コ.

## Rows across keys

No row letter occurs in both the へ and ヤ keys. The へ key has 13 row letters and the ヤ key 6, so with ~47 kana to
choose from you'd expect about two in common. The columns are different: ツ is in both keys, at 122°40′ and 125°00′E.
Where the two keys' rows meet, near 14°20′-15°20′N, one alphabet fits all four of the chart's boxes to within 5′:
ラ 14°20′ (M1), ヲ 14°40′ (M6), ヨ 15°00′ (F16), シ 15°20′ (F17, 5′ outside). That needs L4's ソ and 戦史叢書's 15°N
rows to be wrong, and both are second-hand.

So a possible rule is that the base point changes the column letters but not the row letters. If so, the rows can
repeat every 15°: ツ, キ, テ at 12°N for Manila in 1944 and at 27°N for Okinawa in 1945, with a different suffix and in a
different year. That is still the only direct evidence for the 15° repeat. The rule predicts April 1945 rows
エ = 28°00′N, イ = 29°00′N, ラ = 29°20′N, ヲ = 29°40′N, ヨ = 30°00′N, シ = 30°20′N, タ = 32°00′N. Any Kyushu-Okinawa
anchor in those rows would test it. Not in `keys.csv`.

## Subdivision

`jgrid.py check` prints where each anchor sits in its square. The 901st boxes are good to a quarter of a square, so
only coarse patterns show:

- All five 一 sit in the north-west quarter of their squares (L1, F4, F6, F12, M4; 0.21-0.44 east, 0.51-0.89 north).
- The last kana may carry the north-south position: イ is near the top all three times (0.84-0.95). セ is in the bottom
  third all four times (S1, F7, F11, and F16 if ヨ is 15°00′). カ is in the upper part (0.71-0.89) and ク in the lower
  (0.27-0.37).
- But ケ (0.24-0.74), テ (0.56-0.98) and ソ don't fit, and the same 四 turns up at the bottom (セ, エ, ケ) and the top
  (ラ, テ). Fig. 34's 3ク, 4エ and 4ケ, two-thirds of the way down, agree with ク, エ and 四ケ here (0.13-0.37 north).

Decoding it would take anchors with exact positions (a bearing and distance in a narrative, or a US ship's position),
not plotted boxes.

## Sources

- **JACAR**, as above. Codes appear throughout the April 1945 air groups' action reports. The search hits on a code
  only if it falls in the first ~300 characters of OCR text: 谷田部空 爆戦隊, 29 Apr ([C13120001900](https://www.jacar.archives.go.jp/das/image/C13120001900),
  ユヘ四テ, スニ四テ); 762空, 11 Apr ([C13120532400](https://www.jacar.archives.go.jp/das/image/C13120532400), サテ一ア).
- **901st Air Group night-search report, 10-28 Oct 1944** ([C13120398700](https://www.jacar.archives.go.jp/das/image/C13120398700)),
  pp. 37-38 for the charts. The sortie pages give each signal's code and time: 10 Oct p4-5, 11-12 Oct p6, 16 Oct
  p10, 17 Oct p13, 18 Oct p14, 24-25 Oct p21 (Manila), 25-26 Oct p23, 26 Oct p25 (no contacts), 28 Oct p26 (Cavite).
  The pages not listed are radar-sensitivity graphs or haven't been read.
- **Recon 11, 6-11 Apr 1945** ([C13120384700](https://www.jacar.archives.go.jp/das/image/C13120384700)): orders pp. 3-4,
  narrative pp. 11-14, results p37. **Recon 703, 5-6 Apr 1945** ([C13120385000](https://www.jacar.archives.go.jp/das/image/C13120385000)):
  sortie narrative pp. 7-8, signals pp. 11-12, track charts pp. 15-18 (p17 is the 7 April dawn search).
- **戦史叢書** (the official Japanese war history), full scans at the
  [NIDS search site](https://www.nids.mod.go.jp/military_history_search/). Its keyword search names the volume, not the page,
  so I downloaded vols. 17, 36, 37, 56, 93 and 95 and OCR'd them (tesseract `jpn_vert`, in `/tmp`, not kept). Vol. 56
  converts many Leyte codes to "Manila *x*° *y* nm" (pp. 122, 128-129, 207-215; anchors L5-L10). Vol. 36 p. 225 calls
  the system 地点符号 ("used by the Navy"), with ヘリ4セ = Ishigaki 203° 152 nm, 14 Oct 1944. Vol. 17, which covers
  Okinawa, converts only three codes, for 18 Mar 1945.
- **Not found:** the code table itself. The NIDS catalogue has 特定地点符号表 (トチフ, Jan 1945; JACAR
  [C19010086900](https://www.jacar.archives.go.jp/das/image/C19010086900)), but that is a place-name code
  (A = North America … N = Japan), not this grid. No English-language description turned up either.

## Next

1. More April 1945 anchors: any track chart or narrative that gives a code next to a bearing and distance, or US task
   group positions (TG 58.1 and 58.4 war diaries) at the times of the 6-7 April reports. Rows at 28°-30°N would test
   the shared-rows idea above. Recon 11's 6 April track charts (別紙第一ノ一 to 第一ノ五) aren't in C13120384700. They
   may be filed separately on JACAR. Recon 703's other night searches (later 戦闘詳報 of the 801st) would give more own
   positions like O6-O8.
2. メム三ス (Recon 11's order) against メツ三ス (the 210th): check the 0800 signal itself in Recon 11's log.
3. US positions for the 901st's contacts: TF 38's track for the nights of 11/12 and 16/17 Oct would show whether the
   chart or the crews were right about コヌ四エ and レス四セ.
4. The sortie pages not read yet (pp. 9, 16-20) may have more signals; 14 Oct (ヘリ4セ) and 27 Oct (ツシ二ケへ) aren't
   identified.
5. The subdivision needs exact anchors (see above).
