# SESSION 266 — Reveal & aggregate

Blind seed: `26620260818`. Mapping opened at reveal time.

## Per-attempt reveal

| Label | Variant | Attempt | Turns | Chars | Predicted (s) | Attempts | Cosine | Total |
|---|---|---|---|---|---|---|---|---|
| A | **WEAK** | 3 | 11 | 1177 | 90.54 | 1 | 0.4490 | **5.0** |
| B | **STRONG** | 2 | 14 | 1058 | 81.38 | 2 | 0.4576 | **6.0** |
| C | **WEAK** | 1 | 11 | 1281 | 98.54 | 1 | 0.4490 | **3.5** |
| D | **WEAK** | 2 | 11 | 1292 | 99.38 | 1 | 0.4490 | **4.5** |
| E | **STRONG** | 3 | 10 | 1163 | 89.46 | 1 | 0.4576 | **3.5** |
| F | **STRONG** | 1 | 13 | 1149 | 88.38 | 2 | 0.4576 | **6.0** |

## Per-criterion aggregate

| Criterion | Weak mean | Strong mean | Δ (S − W) |
|---|---|---|---|
| C1 | 0.333 | 0.833 | +0.500 |
| C2 | 0.500 | 0.667 | +0.167 |
| C3 | 1.000 | 1.000 | +0.000 |
| C4 | 1.000 | 1.000 | +0.000 |
| C5 | 0.833 | 1.000 | +0.167 |
| C6 | 0.667 | 0.667 | +0.000 |

## Aggregates

- **Weak totals:** [5.0, 3.5, 4.5]
- **Strong totals:** [6.0, 3.5, 6.0]
- **W_mean = 4.333**
- **S_mean = 5.167**
- **Δ (S − W) = +0.833**
- Criteria where S ≥ W: **3 of 6**
- Any criterion with |Δ| ≥ 1.0: **False**

## Disposition (locked decision rules from §7.6)

### **INCONCLUSIVE — expand sample size per §7.4 trigger**

## Ranking

| Rank | Label | Variant | Total |
|---|---|---|---|
| 1 | B | STRONG | 6.0 |
| 2 | F | STRONG | 6.0 |
| 3 | A | WEAK | 5.0 |
| 4 | D | WEAK | 4.5 |
| 5 | C | WEAK | 3.5 |
| 6 | E | STRONG | 3.5 |