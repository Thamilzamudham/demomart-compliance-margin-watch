Power BI portfolio project: promotion, returns, invoice and margin compliance for a fictional UAE online retailer (synthetic data).

# DemoMart Compliance and Margin Watch

A Power BI portfolio project that combines **business analysis** (requirements, user stories, rules) with **data analysis** (SQL/Python validation, data modelling, DAX, dashboards) for a UAE online retailer.

> **All data in this repository is synthetic.** DemoMart is a fictional company. No real company or customer data is used.

---

## The business enquiry

> **As the Head of E-commerce** at DemoMart, I want **one monthly view** that shows where our promotions, returns, card payments and invoices break our compliance rules, and how much margin each problem costs, so that I can **fix the biggest issues before the next sale event**.

Full requirements, five user stories with acceptance criteria, business rules and KPI definitions:
[`docs/01_business_enquiry_and_requirements.md`](docs/01_business_enquiry_and_requirements.md)

## What the report will answer

| # | Question | Stakeholder |
| --- | --- | --- |
| US-01 | Which promotions advertised a "was price" that was not genuinely charged? | Category Manager |
| US-02 | What do returns cost, and which are caused by our own failures? | Operations Manager |
| US-03 | Are our invoices complete and consistent (tax number, VAT, dates, duplicates)? | Finance Controller |
| US-04 | Where does margin leak between list price and net margin? | Head of E-commerce |
| US-05 | Which orders carry a card surcharge? | Compliance Officer |

> The compliance rules are **internal policy rules modelled for this project**. They are not legal advice or a statement of UAE law.

## Data (synthetic)

Period: 1 Nov 2025 to 31 Oct 2026. Seed 42, about 45,800 orders, 743 promotions, 310 products, 25 sellers.

| File | What it holds |
| --- | --- |
| `data/dim_product.csv`, `dim_seller.csv`, `dim_date.csv` | Dimensions |
| `data/fact_price_history.csv` | Actual selling price per product per day |
| `data/fact_promotions.csv` | Advertised was price and promo price |
| `data/fact_orders.csv`, `fact_returns.csv`, `fact_invoices.csv` | Transactions |
| `data/ground_truth_planted_issues.csv` | Answer key of planted problems. **Do not load into the report.** Used to test detection logic. |
| `data/_generation_summary.json` | Row counts and a self-check of the promotion rule |

Problems are planted deliberately (fake discounts, card surcharges, invoice errors, recurring defects) so every detection can be tested against the answer key.

## Repository structure

```
demomart-compliance-margin-watch/
├── README.md
├── requirements.txt
├── docs/
│   └── 01_business_enquiry_and_requirements.md
├── python/
│   └── generate_data.py
└── data/            (generated CSV files)
```

## How to reproduce the data (no installation on your own computer)

**Option A: GitHub Codespaces (runs in the browser)**

1. On the repository page choose **Code > Codespaces > Create codespace on main**.
2. In the terminal run:
   ```
   pip install -r requirements.txt
   python python/generate_data.py
   ```
3. The CSV files appear in `data/`. Commit them from the Source Control panel.

**Option B: Google Colab**

1. Upload `python/generate_data.py` to a new Colab notebook session.
2. Run `!pip install pandas numpy` then `!python generate_data.py --out data`.
3. Download the `data` folder.

**Option C: use the CSV files already in this repository** (nothing to run).

Options: `--seed 7` changes the random data, `--scale 0.5` halves the order volume.

## Roadmap

- [x] **Step 1:** Requirements, user stories and synthetic data
- [ ] **Step 2:** Data profiling and validation checks in Python
- [ ] **Step 3:** Power BI data model (star schema, relationships, date table)
- [ ] **Step 4:** DAX measures for every KPI
- [ ] **Step 5:** Report pages and design
- [ ] **Step 6:** Insights, recommendations and case study

## Skills demonstrated

Requirements analysis, user stories and acceptance criteria, KPI definition, Python (pandas, NumPy), data validation, Power BI modelling and DAX, dashboard design, stakeholder-ready recommendations.

## Author

**Thamilzamudham Palanisamy** | Data and Business Analyst | Dubai, UAE
LinkedIn: https://www.linkedin.com/in/thamilzamudham-palanisamy-932923202
