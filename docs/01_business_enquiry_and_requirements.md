# 01. Business Enquiry, User Stories and Requirements

**Project:** DemoMart Compliance and Margin Watch
**Author:** Thamilzamudham Palanisamy
**Version:** 0.1 (draft for review) | **Date:** 31 October 2026
**Data:** 100% synthetic. DemoMart is a fictional UAE online retailer. No real company data is used.

---

## 1. The business enquiry

### Original question

> Are our promotions and returns compliant, and where are we losing margin?

**Why it needs fixing before any dashboard is built:**

- "Compliant" is undefined. Compliant with what rule, measured how?
- It is two questions in one (compliance and margin).
- It has no owner, no time frame and no success measure.

### Rewritten enquiry (epic)

> As the **Head of E-commerce** at DemoMart, I want **one monthly view** that shows where our promotions, returns, card payments and invoices break our compliance rules, and how much margin each problem costs, so that I can **fix the biggest issues before the next sale event** (for example White Friday).

---

## 2. Stakeholders

| Role | Interest | Used in stories |
| --- | --- | --- |
| Head of E-commerce (sponsor) | Overall risk and margin picture, decides priorities | Epic, US-04 |
| Category Manager | Promotion pricing and discount claims | US-01 |
| Operations Manager | Returns volume, cost and root causes | US-02 |
| Finance Controller | Invoice completeness and VAT accuracy, margin | US-03, US-04 |
| Compliance Officer | Rule breaches that need action | US-01, US-02, US-05 |

---

## 3. User stories and acceptance criteria

### US-01 Promotion integrity (Category Manager)

**As a** Category Manager, **I want** to see which promotions advertised a "was price" that was not genuinely charged before the sale, **so that** I can correct or withdraw misleading offers.

Acceptance criteria:

1. Each promotion is marked **Pass** or **Fail** against rule PR-1, and **Review** if it also breaches PR-2.
2. The report shows the failure rate and the **overstated discount in AED**, by event, category and seller.
3. A user can drill down from a seller to the individual failing promotions, with the price history chart for each.
4. Rules and thresholds are shown on a Definitions page.

### US-02 Returns cost and causes (Operations Manager)

**As an** Operations Manager, **I want** to see return rate and return cost by category, seller and reason, **so that** I know which returns are caused by our own failures and which are discretionary.

Acceptance criteria:

1. Return rate = returned orders / delivered orders, shown by category, seller and month.
2. Returns are split into **defect or fulfilment-related** (defective, wrong item, late delivery, not as described) and **customer-choice** (changed mind, size or fit).
3. Return cost in AED includes return shipping and written-off stock.
4. Products meeting rule PR-4 (recurring defects) appear in a watch list.

### US-03 Invoice readiness (Finance Controller)

**As a** Finance Controller, **I want** a data quality scorecard for invoices, **so that** gaps are fixed before e-invoicing obligations apply.

Acceptance criteria:

1. Every invoice is checked against rule PR-5 (five checks, listed below).
2. The scorecard shows pass rate per check and overall, by month and seller.
3. Failing invoices are listed with the reason so Finance can correct them.
4. Orders with no invoice at all are counted separately.

### US-04 Margin leakage (Head of E-commerce, Finance Controller)

**As the** Head of E-commerce, **I want** a margin bridge from list-price margin to net margin, **so that** I can see which leakages are largest.

Acceptance criteria:

1. A waterfall shows: margin at regular price, discounts, shipping subsidy, return cost, net margin (all excluding VAT, in AED).
2. It can be filtered by category, seller type, event and month.
3. Net margin % is shown for each category, ranked.
4. The page states the top three leakages in a one-line headline each.

### US-05 Card surcharge check (Compliance Officer)

**As a** Compliance Officer, **I want** to see orders where a card payment surcharge was added, **so that** I can stop the practice and calculate the amount to refund.

Acceptance criteria:

1. Orders with a surcharge above AED 0 are flagged under rule PR-3.
2. Total surcharge exposure in AED is shown by seller and month.
3. The list of flagged orders can be exported from the report.

---

## 4. Business rules used in this project

> **Important:** these are **internal policy rules modelled for this portfolio project**. They are designed to be testable with data. They are **not a statement of UAE law**. Check current regulations before applying any rule in a real business.

| ID | Rule | Test |
| --- | --- | --- |
| PR-1 | The advertised "was price" must have been genuinely charged before the promotion | Count days in the 30 days before the promotion start when the actual selling price was within 5% of the was price. Fail if fewer than **14** days. |
| PR-2 | Very deep discounts get a manual review | Advertised discount above **50%** is marked Review. |
| PR-3 | No surcharge for paying by card | Fail if card surcharge is greater than AED 0. |
| PR-4 | Recurring product defects are escalated | A product with **3 or more** defect-related returns in the 12-month period goes on the watch list (project proxy for repeated defects). |
| PR-5 | Invoices must be complete and consistent | Five checks: (a) seller tax registration number present, (b) VAT equals total x 5/105 within AED 0.05, (c) invoice ID unique, (d) invoice date present and not before the order date, (e) an invoice exists for every order. |

---

## 5. KPI definitions

All money is in **AED**. Revenue and margin are **excluding VAT** (selling prices include 5% VAT, cost prices do not).

| KPI | Definition |
| --- | --- |
| Promo Fail Rate | Promotions failing PR-1 / total promotions |
| Advertised Discount % | (was price - promo price) / was price |
| True Discount % | (average price in the 30 days before the promotion - promo price) / that average price |
| Overstated Discount AED | (advertised discount % - true discount %) x was price x units sold during the promotion |
| Return Rate | Returned orders / delivered orders |
| Return Cost AED | Return shipping + cost of goods written off (units not restocked) |
| Net Revenue ex VAT | (Sales incl. VAT + shipping fees charged - refunds) / 1.05 |
| Net Margin AED | Net revenue ex VAT - cost of goods sold (net of restocked returns) - outbound shipping cost - return shipping cost |
| Net Margin % | Net Margin AED / Net Revenue ex VAT |
| Invoice Pass Rate | Invoices passing all PR-5 checks / total invoices |
| Surcharge Exposure AED | Sum of card surcharges charged |

---

## 6. Data requirements

| Table | Grain (one row per) | Purpose |
| --- | --- | --- |
| dim_product | Product | Category, cost price, seller |
| dim_seller | Seller | First-party or marketplace, tax registration number |
| dim_date | Calendar day | Date table with sale event labels |
| fact_price_history | Product per day | Actual selling price (evidence for PR-1) |
| fact_promotions | Promotion | Advertised was price, promo price, dates |
| fact_orders | Order | Price, quantity, shipping, payment, surcharge |
| fact_returns | Returned order | Reason, refund, restock, return shipping |
| fact_invoices | Invoice | Tax registration number, VAT, dates |
| ground_truth_planted_issues | Planted issue | Answer key to test detection logic. **Not loaded into the report.** |

---

## 7. Non-functional requirements

- Monthly refresh. Report loads in under 5 seconds on a normal laptop.
- Every measure is documented on a Definitions page, using the wording in this file.
- Colour use is accessible: red, amber and green only for status, with labels not colour alone.
- Currency in AED, English labels first. Arabic labels are an optional later improvement.

## 8. Out of scope

- Real-time monitoring, forecasting, customer-level analysis.
- Legal advice or confirmation of regulatory compliance.
- Any real retailer's data.

## 9. Assumptions and limitations

- Data covers **1 November 2025 to 31 October 2026**. Sale event dates (White Friday, Dubai Shopping Festival, Ramadan, Eid, Summer, Back to School) are **approximate**.
- All orders are delivered. Returns after 31 October 2026 are not yet visible, so late-October orders look slightly better than they will.
- Problems are **deliberately planted** at known rates so detection logic can be tested. Real rates will differ.
- Prices include 5% VAT. Cost prices exclude VAT.

## 10. Definition of done

- [ ] Five user stories implemented and each acceptance criterion tested.
- [ ] Detection results compared with `ground_truth_planted_issues.csv` and the match rate reported.
- [ ] Definitions page matches this document.
- [ ] Case study with three insights, each with a recommended action.
- [ ] README explains how to reproduce the data and open the report.
