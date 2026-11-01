#!/usr/bin/env python3
"""
DemoMart Compliance and Margin Watch - synthetic data generator.

Creates CSV files for a FICTIONAL UAE online retailer ("DemoMart").
All data is synthetic. Problems (fake discounts, card surcharges, invoice
errors, recurring defects) are planted at known rates so detection logic can
be tested against an answer key (ground_truth_planted_issues.csv).

Usage:
    python python/generate_data.py                  # writes to ./data
    python python/generate_data.py --seed 7 --scale 0.5
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------
# Settings
# --------------------------------------------------------------------------
START = pd.Timestamp("2025-11-01")
END = pd.Timestamp("2026-10-31")
VAT_RATE = 0.05
FREE_SHIPPING_THRESHOLD = 100.0   # AED, order value incl. VAT
FLAT_SHIPPING_FEE = 12.0          # AED charged below the threshold
BASE_ORDERS_PER_DAY = 105
PROMO_GAP_DAYS = 21               # regular-price days enforced after each promotion

RISKY_SELLERS = {"S03", "S09", "S15", "S21"}  # sellers with more planted problems

CATEGORIES = {
    "Electronics":    dict(n=60, cost=(80, 1800), margin=(0.12, 0.28), ret=0.09, defect=0.45, promo=0.30),
    "Fashion":        dict(n=80, cost=(25, 350),  margin=(0.40, 0.65), ret=0.22, defect=0.12, promo=0.40),
    "Home & Kitchen": dict(n=60, cost=(20, 600),  margin=(0.25, 0.45), ret=0.08, defect=0.30, promo=0.30),
    "Beauty":         dict(n=40, cost=(10, 220),  margin=(0.35, 0.60), ret=0.05, defect=0.15, promo=0.35),
    "Grocery":        dict(n=40, cost=(3, 60),    margin=(0.10, 0.22), ret=0.02, defect=0.35, promo=0.15),
    "Toys & Baby":    dict(n=30, cost=(15, 300),  margin=(0.30, 0.50), ret=0.07, defect=0.30, promo=0.30),
}

# Approximate sale windows (name, start, end, order-volume multiplier)
EVENTS = [
    ("White Friday",            "2025-11-21", "2025-11-30", 1.8),
    ("Dubai Shopping Festival", "2025-12-12", "2026-01-11", 1.3),
    ("Ramadan Deals",           "2026-02-18", "2026-03-19", 1.25),
    ("Eid Sale",                "2026-03-20", "2026-03-31", 1.4),
    ("Eid Al Adha Offers",      "2026-05-25", "2026-06-02", 1.3),
    ("Summer Surprises",        "2026-06-26", "2026-08-30", 1.1),
    ("Back to School",          "2026-08-31", "2026-09-20", 1.2),
]

CITIES = ["Dubai", "Abu Dhabi", "Sharjah", "Ajman", "Al Ain", "Ras Al Khaimah", "Fujairah"]
CITY_WEIGHTS = [0.45, 0.20, 0.15, 0.05, 0.07, 0.05, 0.03]
CITY_SHIP_COST = {"Dubai": 9, "Sharjah": 10, "Ajman": 10, "Abu Dhabi": 12,
                  "Al Ain": 14, "Ras Al Khaimah": 15, "Fujairah": 16}

PAYMENT_METHODS = ["Card", "Cash on Delivery", "Apple Pay", "Wallet"]
PAYMENT_WEIGHTS = [0.50, 0.22, 0.18, 0.10]

DISC_PCT = np.array([10, 15, 20, 25, 30, 40, 50, 60])
DISC_PROB = np.array([0.14, 0.20, 0.22, 0.18, 0.12, 0.08, 0.04, 0.02])

DEFECT_REASON = "Defective / not working"


# --------------------------------------------------------------------------
# Dimension tables
# --------------------------------------------------------------------------
def build_sellers(rng: np.random.Generator) -> pd.DataFrame:
    rows = [dict(seller_id="S00", seller_name="DemoMart Retail", seller_type="First-party",
                 seller_trn="100" + "".join(str(x) for x in rng.integers(0, 10, 12)))]
    for i in range(1, 25):
        rows.append(dict(
            seller_id=f"S{i:02d}",
            seller_name=f"Marketplace Seller {i:02d}",
            seller_type="Marketplace",
            seller_trn="100" + "".join(str(x) for x in rng.integers(0, 10, 12)),
        ))
    return pd.DataFrame(rows)


def build_products(rng: np.random.Generator, sellers: pd.DataFrame) -> pd.DataFrame:
    market = [s for s in sellers["seller_id"] if s != "S00"]
    weights = np.array([0.35] + [(0.65 / len(market)) * (1.3 if s in RISKY_SELLERS else 1.0) for s in market])
    weights = weights / weights.sum()
    seller_ids = ["S00"] + market

    rows = []
    pid = 1
    for cat, cfg in CATEGORIES.items():
        for _ in range(cfg["n"]):
            cost = float(np.exp(rng.uniform(np.log(cfg["cost"][0]), np.log(cfg["cost"][1]))))
            margin = rng.uniform(*cfg["margin"])
            price_incl_vat = cost / (1 - margin) * (1 + VAT_RATE)
            rows.append(dict(
                product_id=f"P{pid:04d}",
                product_name=f"{cat} Item {pid:03d}",
                category=cat,
                brand=f"Brand {chr(65 + int(rng.integers(0, 12)))}",
                seller_id=str(rng.choice(seller_ids, p=weights)),
                cost_price_aed=round(cost, 2),
                base_price_aed=round(price_incl_vat, 2),
            ))
            pid += 1
    return pd.DataFrame(rows)


def build_dim_date(dates: pd.DatetimeIndex) -> pd.DataFrame:
    event = np.array(["None"] * len(dates), dtype=object)
    for name, s, e, _ in EVENTS:
        event[(dates >= pd.Timestamp(s)) & (dates <= pd.Timestamp(e))] = name
    return pd.DataFrame(dict(
        date=dates.strftime("%Y-%m-%d"),
        year=dates.year,
        month_num=dates.month,
        month_name=dates.strftime("%B"),
        year_month=dates.strftime("%Y-%m"),
        iso_week=dates.isocalendar().week.to_numpy(),
        day_name=dates.strftime("%A"),
        is_weekend=(dates.dayofweek >= 5).astype(int),  # UAE weekend: Saturday and Sunday
        event_name=event,
    ))


# --------------------------------------------------------------------------
# Prices and promotions
# --------------------------------------------------------------------------
def build_prices_and_promos(rng, products: pd.DataFrame, dates: pd.DatetimeIndex):
    P, D = len(products), len(dates)
    day = np.arange(D)
    drift_rate = rng.uniform(0.2, 1.0, P)
    base = np.round(products["base_price_aed"].to_numpy()[:, None] * (1 + 0.0002 * np.outer(drift_rate, day)), 2)

    price = base.copy()                      # actual selling price (what customers paid)
    was = np.full((P, D), np.nan)            # advertised "was price" shown on promo days
    occ = np.zeros((P, D), dtype=bool)       # promo + pre-sale + gap occupancy

    risky_prod = products["seller_id"].isin(RISKY_SELLERS).to_numpy()
    cat = products["category"].to_numpy()

    # Candidate promotions: (start_idx, product_idx, event_name, end_idx)
    cands = []
    for name, s, e, _ in EVENTS:
        si, ei = (pd.Timestamp(s) - START).days, (pd.Timestamp(e) - START).days
        for p in range(P):
            if rng.random() < CATEGORIES[cat[p]]["promo"]:
                start = int(rng.integers(max(si, 20), max(si, 20, ei - 4) + 1))
                dur = int(rng.integers(5, 22))
                cands.append((start, p, name, min(start + dur - 1, ei)))
    for _ in range(150):
        p = int(rng.integers(0, P))
        start = int(rng.integers(20, D - 7))
        cands.append((start, p, "Everyday Deal", start + 6))
    cands.sort(key=lambda c: (c[0], c[1]))

    promo_rows, truth = [], []
    for start, p, ev, end in cands:
        if end < start or occ[p, start:end + 1].any():
            continue
        planted = rng.random() < (0.40 if risky_prod[p] else 0.05)
        regular = float(base[p, start])
        hike_days = 0
        variant = None
        if planted:
            variant = "price_hike" if rng.random() < 0.4 else "inflated_was_price"
            if variant == "price_hike":
                hike_days = int(rng.integers(6, 11))
                if start - hike_days < 0 or occ[p, start - hike_days:start].any():
                    variant, hike_days = "inflated_was_price", 0

        if variant is None:
            was_price = regular
            promo_price = regular * (1 - rng.choice(DISC_PCT, p=DISC_PROB) / 100)
        elif variant == "inflated_was_price":
            was_price = regular * rng.uniform(1.3, 1.7)
            promo_price = regular * (1 - rng.uniform(0.0, 0.08))
        else:  # price_hike: raise the price for a few days, then "discount" back to normal
            was_price = regular * rng.uniform(1.25, 1.45)
            promo_price = regular * rng.uniform(0.92, 1.0)
            price[p, start - hike_days:start] = round(was_price, 2)

        was_price, promo_price = round(was_price, 2), round(promo_price, 2)
        price[p, start:end + 1] = promo_price
        was[p, start:end + 1] = was_price
        occ[p, start - hike_days:min(D, end + 1 + PROMO_GAP_DAYS)] = True

        promo_rows.append(dict(
            event_name=ev,
            product_id=products["product_id"].iloc[p],
            seller_id=products["seller_id"].iloc[p],
            start_date=dates[start].strftime("%Y-%m-%d"),
            end_date=dates[end].strftime("%Y-%m-%d"),
            advertised_was_price_aed=was_price,
            promo_price_aed=promo_price,
            advertised_discount_pct=round((was_price - promo_price) / was_price * 100, 1),
        ))
        truth.append(variant)

    promos = pd.DataFrame(promo_rows)
    promos.insert(0, "promo_id", [f"PR{i:05d}" for i in range(1, len(promos) + 1)])
    gt = pd.DataFrame(dict(
        issue_type=[f"promo_{v}" for v in truth if v],
        entity_type="promo_id",
        entity_id=[pid for pid, v in zip(promos["promo_id"], truth) if v],
    ))
    return np.round(price, 2), was, base, promos, gt


# --------------------------------------------------------------------------
# Orders, returns, invoices
# --------------------------------------------------------------------------
def build_orders(rng, products, sellers, dates, price, was, base, scale):
    P, D = price.shape
    on_promo = ~np.isnan(was)
    mult = np.ones(D)
    for _, s, e, m in EVENTS:
        mult[(pd.Timestamp(s) - START).days:(pd.Timestamp(e) - START).days + 1] = m
    popularity = rng.lognormal(0, 0.8, P)

    day_chunks, prod_chunks = [], []
    for d in range(D):
        lam = BASE_ORDERS_PER_DAY * scale * mult[d] * (1.15 if dates[d].dayofweek >= 4 else 1.0)
        n = int(rng.poisson(lam))
        w = popularity * (1 + 2 * on_promo[:, d])
        prod_chunks.append(rng.choice(P, size=n, p=w / w.sum()))
        day_chunks.append(np.full(n, d))
    day_idx = np.concatenate(day_chunks)
    pidx = np.concatenate(prod_chunks)
    n = len(day_idx)

    cat = products["category"].to_numpy()[pidx]
    qty = np.where(cat == "Grocery", 1 + rng.poisson(1.5, n),
                   rng.choice([1, 2, 3], size=n, p=[0.85, 0.12, 0.03]))
    selling = price[pidx, day_idx]
    regular = base[pidx, day_idx]
    was_p = was[pidx, day_idx]
    order_value = selling * qty

    city = rng.choice(CITIES, size=n, p=CITY_WEIGHTS)
    ship_cost = np.maximum(6, np.array([CITY_SHIP_COST[c] for c in city]) + rng.normal(0, 1.2, n))
    ship_fee = np.where(order_value >= FREE_SHIPPING_THRESHOLD, 0.0, FLAT_SHIPPING_FEE)
    pay = rng.choice(PAYMENT_METHODS, size=n, p=PAYMENT_WEIGHTS)

    seller_id = products["seller_id"].to_numpy()[pidx]
    risky_o = np.isin(seller_id, list(RISKY_SELLERS))
    surcharge_on = risky_o & (pay == "Card") & (rng.random(n) < 0.40)
    surcharge = np.where(surcharge_on, order_value * rng.uniform(0.015, 0.025, n), 0.0)

    orders = pd.DataFrame(dict(
        order_id=[f"O{i:07d}" for i in range(1, n + 1)],
        order_date=dates[day_idx].strftime("%Y-%m-%d"),
        product_id=products["product_id"].to_numpy()[pidx],
        seller_id=seller_id,
        customer_city=city,
        quantity=qty,
        regular_price_aed=np.round(regular, 2),
        selling_price_aed=np.round(selling, 2),
        advertised_was_price_aed=np.round(was_p, 2),
        shipping_fee_charged_aed=ship_fee,
        shipping_cost_aed=np.round(ship_cost, 2),
        payment_method=pay,
        card_surcharge_aed=np.round(surcharge, 2),
    ))
    gt = pd.DataFrame(dict(
        issue_type="card_surcharge",
        entity_type="order_id",
        entity_id=orders.loc[surcharge_on, "order_id"].to_numpy(),
    ))
    return orders, pidx, day_idx, gt


def build_returns(rng, products, orders, pidx, day_idx, dates):
    n = len(orders)
    cat_arr = products["category"].to_numpy()
    ret_rate = np.array([CATEGORIES[c]["ret"] for c in cat_arr])
    defect_share = np.array([CATEGORIES[c]["defect"] for c in cat_arr])

    # Recurring-defect "problem products" (planted)
    pool = np.where(np.isin(cat_arr, ["Electronics", "Home & Kitchen"]))[0]
    problem = rng.choice(pool, size=6, replace=False)
    problem_mask = np.zeros(len(products), dtype=bool)
    problem_mask[problem] = True
    defect_share = np.where(problem_mask, 0.90, defect_share)

    risky_o = np.isin(orders["seller_id"].to_numpy(), list(RISKY_SELLERS))
    p_ret = ret_rate[pidx] * np.where(risky_o, 1.4, 1.0)
    p_ret = np.where(problem_mask[pidx], np.minimum(p_ret * 3, 0.60), p_ret)
    is_ret = rng.random(n) < p_ret
    days_after = rng.integers(2, 26, n)
    ret_day = day_idx + days_after
    is_ret &= ret_day < len(dates)          # returns after the data end are not visible yet

    sel = np.where(is_ret)[0]
    m = len(sel)
    defect = rng.random(m) < defect_share[pidx[sel]]
    cat_ret = cat_arr[pidx[sel]]
    reason = np.empty(m, dtype=object)
    reason[defect] = DEFECT_REASON
    for c in CATEGORIES:
        mask = (~defect) & (cat_ret == c)
        if not mask.any():
            continue
        if c == "Fashion":
            opts, probs = ["Size / fit", "Changed mind", "Not as described", "Wrong item delivered", "Late delivery"], [.45, .25, .15, .10, .05]
        else:
            opts, probs = ["Changed mind", "Not as described", "Wrong item delivered", "Late delivery"], [.40, .30, .20, .10]
        reason[mask] = rng.choice(opts, size=int(mask.sum()), p=probs)

    sub = orders.iloc[sel]
    order_value = (sub["selling_price_aed"] * sub["quantity"]).to_numpy()
    full = rng.random(m) < 0.90
    refund = np.where(full, order_value, order_value * rng.uniform(0.5, 0.9, m))
    restocked = np.where(defect, rng.random(m) < 0.30, rng.random(m) < 0.85)
    cost = products["cost_price_aed"].to_numpy()[pidx[sel]] * sub["quantity"].to_numpy()

    returns = pd.DataFrame(dict(
        return_id=[f"R{i:07d}" for i in range(1, m + 1)],
        order_id=sub["order_id"].to_numpy(),
        return_date=dates[ret_day[sel]].strftime("%Y-%m-%d"),
        return_reason=reason,
        is_defect_related=defect.astype(int),
        refund_amount_aed=np.round(refund, 2),
        restocked=restocked.astype(int),
        cogs_recovered_aed=np.round(np.where(restocked, cost, 0.0), 2),
        return_shipping_cost_aed=np.round(rng.uniform(10, 22, m), 2),
    ))
    gt = pd.DataFrame(dict(
        issue_type="recurring_defect_product",
        entity_type="product_id",
        entity_id=products["product_id"].to_numpy()[problem],
    ))
    return returns, gt


def build_invoices(rng, orders, sellers):
    n = len(orders)
    trn = orders["seller_id"].map(sellers.set_index("seller_id")["seller_trn"]).to_numpy(dtype=object)
    total = (orders["selling_price_aed"] * orders["quantity"] + orders["shipping_fee_charged_aed"]).to_numpy()
    vat = total * VAT_RATE / (1 + VAT_RATE)
    risky_o = np.isin(orders["seller_id"].to_numpy(), list(RISKY_SELLERS))
    first_party = orders["seller_id"].to_numpy() == "S00"

    no_inv = rng.random(n) < 0.02
    miss_trn = (rng.random(n) < np.where(risky_o, 0.08, 0.015)) & ~first_party
    vat_bad = rng.random(n) < 0.02
    vat_zero = rng.random(n) < 0.5
    date_before = rng.random(n) < 0.01
    date_null = rng.random(n) < 0.008
    dup = rng.random(n) < 0.01

    vat = np.where(vat_bad, np.where(vat_zero, 0.0, total * VAT_RATE), vat)
    trn = np.where(miss_trn, None, trn)

    odate = pd.to_datetime(orders["order_date"])
    offset = np.where(rng.random(n) < 0.2, 1, 0)
    back = rng.integers(1, 6, n)
    inv_date = odate + pd.to_timedelta(np.where(date_before, -back, offset), unit="D")
    inv_date = inv_date.where(~date_null, pd.NaT)

    inv = pd.DataFrame(dict(
        invoice_id=["INV-" + oid[1:] for oid in orders["order_id"]],
        order_id=orders["order_id"].to_numpy(),
        invoice_date=inv_date.dt.strftime("%Y-%m-%d"),
        seller_id=orders["seller_id"].to_numpy(),
        seller_trn=trn,
        currency="AED",
        total_amount_aed=np.round(total, 2),
        vat_amount_aed=np.round(vat, 2),
    ))
    inv["net_amount_aed"] = (inv["total_amount_aed"] - inv["vat_amount_aed"]).round(2)

    keep = ~no_inv
    truth = []

    def add(kind, mask, col="invoice_id"):
        ids = inv.loc[mask & keep, col].to_numpy()
        truth.append(pd.DataFrame(dict(issue_type=kind, entity_type=col, entity_id=ids)))

    add("invoice_missing_trn", miss_trn)
    add("invoice_vat_mismatch", vat_bad)
    add("invoice_date_before_order", date_before & ~date_null)
    add("invoice_date_missing", date_null)
    add("invoice_duplicate", dup)
    truth.append(pd.DataFrame(dict(issue_type="invoice_missing", entity_type="order_id",
                                   entity_id=inv.loc[no_inv, "order_id"].to_numpy())))

    out = pd.concat([inv[keep], inv[keep & dup]], ignore_index=True)
    out = out.sort_values(["invoice_id"], kind="stable").reset_index(drop=True)
    return out, pd.concat(truth, ignore_index=True)


# --------------------------------------------------------------------------
# Checks and main
# --------------------------------------------------------------------------
def sanity_checks(tables, price, dates, promos, gt_all):
    prod, sell, orders, rets, inv = (tables[k] for k in
                                     ("dim_product", "dim_seller", "fact_orders", "fact_returns", "fact_invoices"))
    assert prod["product_id"].is_unique and sell["seller_id"].is_unique
    assert orders["order_id"].is_unique and rets["return_id"].is_unique
    assert orders["product_id"].isin(prod["product_id"]).all()
    assert orders["seller_id"].isin(sell["seller_id"]).all()
    assert rets["order_id"].isin(orders["order_id"]).all()
    assert promos["product_id"].isin(prod["product_id"]).all()

    # Re-test rule PR-1 from the price history and compare with the answer key
    pid_index = {p: i for i, p in enumerate(prod["product_id"])}
    date_index = {d: i for i, d in enumerate(dates.strftime("%Y-%m-%d"))}
    fail = []
    for r in promos.itertuples():
        p, s = pid_index[r.product_id], date_index[r.start_date]
        window = price[p, max(0, s - 30):s]
        days_at_was = int((np.abs(window / r.advertised_was_price_aed - 1) <= 0.05).sum())
        fail.append(days_at_was < 14)
    flagged = set(promos.loc[np.array(fail), "promo_id"])
    planted = set(gt_all.loc[gt_all["entity_type"] == "promo_id", "entity_id"])
    tp, fp, fn = len(flagged & planted), len(flagged - planted), len(planted - flagged)
    return dict(pr1_flagged=len(flagged), pr1_planted=len(planted),
                pr1_true_positive=tp, pr1_false_positive=fp, pr1_false_negative=fn)


def main():
    ap = argparse.ArgumentParser(description="Generate DemoMart synthetic data")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--scale", type=float, default=1.0, help="order volume multiplier (0.5 = half the rows)")
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parent.parent / "data")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(args.seed)
    dates = pd.date_range(START, END, freq="D")

    sellers = build_sellers(rng)
    products = build_products(rng, sellers)
    price, was, base, promos, gt_promo = build_prices_and_promos(rng, products, dates)
    orders, pidx, day_idx, gt_orders = build_orders(rng, products, sellers, dates, price, was, base, args.scale)
    returns, gt_returns = build_returns(rng, products, orders, pidx, day_idx, dates)
    invoices, gt_inv = build_invoices(rng, orders, sellers)

    price_history = pd.DataFrame(dict(
        product_id=np.repeat(products["product_id"].to_numpy(), len(dates)),
        date=np.tile(dates.strftime("%Y-%m-%d"), len(products)),
        selling_price_aed=price.ravel(),
    ))
    gt_all = pd.concat([gt_promo, gt_orders, gt_returns, gt_inv], ignore_index=True)

    tables = {
        "dim_product": products,
        "dim_seller": sellers,
        "dim_date": build_dim_date(dates),
        "fact_price_history": price_history,
        "fact_promotions": promos,
        "fact_orders": orders,
        "fact_returns": returns,
        "fact_invoices": invoices,
        "ground_truth_planted_issues": gt_all,
    }
    checks = sanity_checks(tables, price, dates, promos, gt_all)

    for name, df in tables.items():
        df.to_csv(args.out / f"{name}.csv", index=False)

    delivered = len(orders)
    summary = dict(
        seed=args.seed,
        scale=args.scale,
        period=f"{START.date()} to {END.date()}",
        rows={k: int(len(v)) for k, v in tables.items()},
        return_rate=round(len(returns) / delivered, 4),
        defect_share_of_returns=round(float(returns["is_defect_related"].mean()), 4),
        promos_over_50pct_advertised=int((promos["advertised_discount_pct"] > 50).sum()),
        planted_issue_counts=gt_all["issue_type"].value_counts().to_dict(),
        pr1_rule_check_vs_answer_key=checks,
    )
    (args.out / "_generation_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
