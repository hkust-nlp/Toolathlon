# Brightwater Home Goods — Carrier Invoice Audit Rules (Meridian Parcel Service)

Applies to invoice **MPS-2025-09-BHG** (`carrier_invoice_2025-09.csv`), which
bills shipments with manifest ship dates from **2025-09-01 to 2025-09-30**.
A few late-August shipments were carried over onto this invoice; they are
audited like any other line. This document is the authoritative rule set for
the monthly audit workbook.

## 1. Sources

| File | Role |
| ---- | ---- |
| `shipment_manifest.csv` | Our shipping system's export. Authoritative for service, destination, weight, dimensions, residential flag, declared value and ship date. Covers 2025-08-27 to 2025-10-03. |
| `carrier_invoice_2025-09.csv` | What the carrier billed, one line per shipment charge, numbered by `invoice_line`. |
| `rate_card_2025.xlsx` | The contract: `Base Rates` (list prices by service, weight and zone), `Zones` (destination ZIP prefix ranges), `Fuel Surcharge` (weekly percentages) and `Contract Terms` (discounts, surcharges, thresholds). |

Reading notes:

1. **Tracking numbers.** On the invoice they may carry stray leading/trailing
   whitespace or lower-case letters (`" mps250912345678"`). Trim whitespace and
   upper-case them before matching. The canonical form is `MPS` followed by
   12 digits.
2. **Postal codes are text.** They may start with `0` (e.g. `01923-4410`).
   Keep the leading zeros; the zone lookup uses the first three characters.
3. **Amounts** are USD with two decimals. On every invoice line
   `total_charge = base_charge + residential_surcharge + declared_value_surcharge + fuel_surcharge`.
4. Neither file is sorted in any particular way except that the invoice is in
   `invoice_line` order.

## 2. Classifying invoice lines

Process the invoice in ascending `invoice_line` order.

1. **Duplicate.** If a (normalised) tracking number appears on more than one
   invoice line, the line with the **lowest** `invoice_line` is audited
   normally; every later line with that tracking number is a **Duplicate**.
2. **Not in manifest.** A line whose tracking number does not appear in the
   manifest at all is **Not in manifest**.
3. Every other line is **audited**: its expected charge is computed from the
   manifest and the rate card (§3) and compared with the invoice (§4).

For Duplicate and Not in manifest lines the whole billed amount is in dispute
(§5).

## 3. Expected charge of an audited line

Round to the cent (round half up) exactly where indicated; everything else is
exact arithmetic.

1. **Service** — the manifest `service` (`Ground`, `Express Saver` or
   `Priority Overnight`). The service printed on the invoice is only used for
   the comparison in §4.
2. **Zone** — take the first three characters of the manifest
   `dest_postal_code` and find the row of the `Zones` sheet with
   `Prefix From ≤ prefix ≤ Prefix To` (inclusive, compared as three-character
   text).
3. **Billable weight**, in whole pounds:
   * Round the actual weight **up** to the next whole pound (a weight that is
     already whole stays as it is), with a minimum of 1 lb.
   * If `length × width × height` is **strictly greater than 1,728 cubic
     inches**, the dimensional weight is `length × width × height ÷ 139`,
     rounded **up** to the next whole pound. Otherwise there is no
     dimensional weight.
   * Billable weight = the greater of the two.
4. **Base charge** — the list price in `Base Rates` for the service, billable
   weight and zone, reduced by the contract discount of that service
   (`Contract Terms`: Ground 20 %, Express Saver 25 %, Priority Overnight
   30 %), rounded to the cent.
5. **Residential surcharge** — `4.50` when the manifest `residential` flag is
   `Y`, otherwise `0.00`.
6. **Declared value surcharge** — `0.00` when the declared value is `100.00`
   or less. Above that, `1.05` for every `100.00` **or fraction thereof** of
   the whole declared value (150.00 → 2 × 1.05 = 2.10; 250.00 → 3.15;
   600.00 → 6.30).
7. **Fuel surcharge** — the percentage of the `Fuel Surcharge` week (Monday
   to Sunday, identified by its `Week Starting (Monday)` date) that contains
   the **manifest ship date**. The ship date printed on the invoice is the
   carrier's scan date, which can be one or more days later, and must not be
   used for this. Apply the percentage to `base charge + residential
   surcharge` only — never to the declared value surcharge — and round to
   the cent.
8. **Expected total** = base charge + residential surcharge + declared value
   surcharge + fuel surcharge.

## 4. Comparing with the invoice

* `Variance = total_charge − Expected total`.
* **Status**: `OK` when the variance is exactly 0.00; `Overbilled` when it is
  positive; `Underbilled` when it is negative.
* **Issues** lists every component of the invoice line that differs from its
  expected value, in this fixed order, separated by `; `:

  | Code | Differs when |
  | ---- | ------------ |
  | `Service` | invoice `service` ≠ manifest service |
  | `Zone` | invoice `zone` ≠ expected zone |
  | `Weight` | invoice `billed_weight_lb` ≠ billable weight |
  | `Base rate` | invoice `base_charge` ≠ expected base charge |
  | `Residential` | invoice `residential_surcharge` ≠ expected residential surcharge |
  | `Declared value` | invoice `declared_value_surcharge` ≠ expected declared value surcharge |
  | `Fuel` | invoice `fuel_surcharge` ≠ expected fuel surcharge |

  Compare each component independently. A wrong zone normally also produces a
  different base charge and a different fuel surcharge, so such a line reads
  `Zone; Base rate; Fuel`. Write `None` when nothing differs (the line is then
  `OK`).
* For Duplicate and Not in manifest lines, `Variance` is the billed
  `total_charge` and `Issues` repeats the status text (`Duplicate` or
  `Not in manifest`).

## 5. Disputes

A line is disputed when it is Overbilled with a variance of **1.00 or more**,
or when it is a Duplicate or Not in manifest line. The disputed amount is the
variance (that is, the full billed amount for Duplicate and Not in manifest
lines). Overbilled lines below 1.00 and all Underbilled lines are reported in
the audit but are **not** disputed.

## 6. Report structure

Use `freight_audit_template.xlsx` exactly (same sheet names, same column
headers, same column order). Save the result as `freight_audit_2025-09.xlsx`
in the workspace. Write literal values (no formulas); money with two decimal
places. Where this document says a cell is empty, leave it empty (do not
write `0`, `-` or `N/A`).

### Sheet `Shipment Audit`

One row per invoice line, sorted by `Invoice Line` ascending. Columns:
`Invoice Line, Tracking Number, Service, Expected Zone, Expected Billed Weight,
Expected Total, Billed Total, Variance, Status, Issues`.

* `Tracking Number` in canonical form.
* `Service`: the manifest service for audited and Duplicate lines; the invoice
  service for Not in manifest lines.
* `Expected Zone`, `Expected Billed Weight` (whole numbers) and
  `Expected Total`: filled for audited lines, **empty** for Duplicate and Not
  in manifest lines.
* `Billed Total` = the invoice `total_charge`.

### Sheet `Service Summary`

One row per service that appears in the `Service` column of the audit sheet,
sorted by `Service` ascending (alphabetical). Columns: `Service, Invoice Lines,
Audited Shipments, Billed Total, Expected Total, Overbilled Amount,
Underbilled Amount, Disputed Lines, Disputed Amount, Unbilled Shipments`.

* `Invoice Lines`: number of audit rows with that service (all statuses).
* `Audited Shipments`: its rows with status OK, Overbilled or Underbilled.
* `Billed Total`: sum of `Billed Total` over all of its rows.
* `Expected Total`: sum of `Expected Total` over its audited rows.
* `Overbilled Amount`: sum of the variances of its Overbilled rows (all of
  them, not only the disputed ones).
* `Underbilled Amount`: sum of the absolute variances of its Underbilled rows,
  reported as a positive number.
* `Disputed Lines` / `Disputed Amount`: the number of its rows on the
  `Disputes` sheet and the sum of their disputed amounts.
* `Unbilled Shipments`: manifest shipments with that service whose ship date
  lies within 2025-09-01..2025-09-30 and whose tracking number is on no
  invoice line. Manifest rows outside that period are ignored here.

### Sheet `Disputes`

One row per disputed line (§5), sorted by `Disputed Amount` descending, then
`Invoice Line` ascending. Columns: `Invoice Line, Tracking Number, Service,
Status, Issues, Disputed Amount`. If nothing is disputed, leave only the
header row.
