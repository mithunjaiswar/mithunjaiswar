# Data Mapping — source CSV → newsletter section

## 1. WBR View CSV

Structure: stacked metric blocks. Each block is a 3-row header then 8 data rows.

```
row h      : <Metric Name> | * | ... | SINGLE | ... | EIP | ... | D2O | ... || <Metric> | Own Now | ... | EV | ... | Revenue Share | ... | Fixed Pay
row h+1    : City | wk1 | wk2 | wk3 | wk4 | WoW | (repeats per product)
row h+2    : *  (= Overall / pan-India)
row h+3..9 : Mumbai, Kolkata, Bangalore, Delhi NCR, Hyderabad, Chennai, Pune
```

**Column offsets** (0-indexed, from the row start). Each product occupies 4 week columns + 1 WoW:

| Product group | week cols | WoW |
|---|---|---|
| Overall (all products) | 2,3,4,5 | 6 |
| SINGLE | 7,8,9,10 | 11 |
| EIP | 12,13,14,15 | 16 |
| D2O | 17,18,19,20 | 21 |
| *(col 22 blank, col 23 = repeated city label)* | | |
| Own Now | 24,25,26,27 | 28 |
| EV | 29,30,31,32 | 33 |
| Revenue Share | 34,35,36,37 | 38 |
| Fixed Pay | 39,40,41,42 | 43 |

> **Trap:** the four week columns run oldest → newest. The current week is the **last** (index +3),
> not the first. Reading col 24 instead of col 27 for Own Now silently yields a 4-week-old figure.

**Blocks used** (header row numbers shift between exports — locate by name in column 1, never by
hard-coded row index):

| Block name in CSV | Newsletter section |
|---|---|
| `Total Collections %` | Total Recovery % (city + product) and KPI row 1 |
| `Total Collections % (w/o DP to OS)` | Collection Without Deposit Conversion, KPI row 2 |
| `Bad Debt %` | Bad Debts % (city + product), KPI row 3 |
| `CarryForward % (OS Bifurcation)` | KPI row 4 |
| `Unique Partners (wt Advance Collections)` | Advance Collections — partner counts block |
| `Advance Collections %` | Advance Collections — % of OS block |

**City-wise tables** read the *Overall* product column (2–6) across the 8 city rows.
**Product-wise tables** read the *Overall city* row (`*`, row h+2) across the product column groups.

### Product display names

The CSV names and the newsletter names differ, and differ *between tables*:

| CSV | Recovery table | Bad Debts table |
|---|---|---|
| SINGLE | Leasing | Single |
| EV | EV Leasing | EV |
| D2O | Drive To Own | Drive To Own |
| EIP | EIP | EIP |
| Own Now | Own Now | Own Now |
| Revenue Share | Revenue Share | Revenue Share |
| Fixed Pay | *omit* | *omit* |

Fixed Pay is excluded — it is `-` for most recent weeks and adds noise.

### WoW units

- Recovery / CtoR / CF OS / Bad Debt / Advance % → **percentage points** (e.g. `-0.7%`)
- Advance partner **counts** → **percent change** (e.g. `+12%` on 589 → 669)

Take the WoW from the CSV column, never recompute from rounded displayed values.

---

## 2. SD_Profiles CSV — Deposit Health

Rows: `City, Cohort, wk1, wk2, wk3, wk4, WoW, ...` — cohort values are the deposit slabs
`<1`, `1-2000`, `2001-5000`, `5001-10000`, `10001-20000`, `20000+` (plus a `Total` row).
`*` in the city column = pan-India.

> **Trap — week offset.** SD_Profiles is typically refreshed **one week ahead** of the WBR View.
> If WBR ends at Aug-10, SD_Profiles will already carry Aug-17. **Always align to the WBR week**
> — pick the column whose header matches the newsletter's reporting week, not the last column.
> Verify the header row before indexing.

Slab → risk label mapping for the table:

| Slab | Risk Level |
|---|---|
| < 1 | – |
| 1 – 2,000 | High Risk (red) |
| 2,001 – 5,000 | Moderate Risk (orange) |
| 5,001 – 10,000 | Low Risk (green) |
| 10,001 – 20,000 | Healthy (green) |
| 20,000+ | Healthy (green) |

City bullets are written as `Good Shape — <City>:` (green) or `Watch — <City>:` (red/orange), using
roll-ups: **≤₹5K** = `<1` + `1-2000` + `2001-5000`; **>₹10K** = `10001-20000` + `20000+`;
**high-risk ≤₹2K** = `<1` + `1-2000`.

---

## 3. Central Car Recovery Dash CSV — Vehicle Recovery Aging

Rows: `Metric, City, <week columns...>`. Week columns run Jun-22 onward — **locate the reporting
week by header name**, do not hard-code.

Metrics used:

| Metric row | Column |
|---|---|
| `Pending <3 Days` | <3d |
| `Pending 3-7 Days` | 3-7d |
| `Pending 8-15 Days` | 8-15d |
| `Pending 16-30 Days` | 16-30d |
| `Pending > 30 Days` | >30d |
| `Overall Pending Recovery` | Pending (total) |
| `Completed P50. TAT (in Hours & Days)` | P50 TAT |

### P50 TAT conversion

The raw value is **`HH:MM`**, i.e. hours and minutes — not days.

```
days = (hours + minutes/60) / 24     → display as "N.Nd"
```

Sanity-check the conversion against the prior newsletter (e.g. Overall `24:08` → `1.0d`).

> **Trap:** the metric name appears **twice** in the file — two blocks with different scopes. The
> **first** occurrence is the correct one. The second yields implausible values (1000+ hours). Guard
> against re-matching.
>
> **Trap:** `0:00` means *no completed recoveries that week*, not "instant". Treat as a data gap; do
> not report it as a best-in-class TAT.

Validation: city `Overall Pending Recovery` values must sum to the `*` row.

---

## 4. Reporting week selection

The newsletter week = the **latest week present in the WBR View**, which lags the calendar by
1–2 weeks. Confirm with the user if the WBR latest week is more than 2 weeks old.
