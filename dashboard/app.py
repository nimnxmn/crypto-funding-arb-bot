import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime, timezone

from strategy.scanner import scan, fetch_all, format_time_until
from paper_trade.simulator import PaperTradeSimulator, LOG_PATH
from risk.manager import check_all, validate_open, ALERT_OK, ALERT_STOPLOSS, ALERT_CRITICAL, ALERT_DRIFT
from config import ROUND_TRIP_FEE, TOTAL_CAPITAL, MAX_POSITION_PCT, STOP_LOSS_PCT, DRIFT_WARNING_PCT, TRADING_MODE
import live.trader as live_trader

st.set_page_config(page_title="ARB_bot", layout="wide", page_icon="🤖")

# ── Helpers ──────────────────────────────────────────────────────────────────

def load_sim() -> PaperTradeSimulator:
    return PaperTradeSimulator()


def get_live_data() -> dict:
    by_base = fetch_all()
    return {
        base: {row["exchange"]: {"funding_rate": row["funding_rate"], "mark_price": row["mark_price"]}
               for row in rows}
        for base, rows in by_base.items()
    }


def build_pnl_chart() -> go.Figure:
    if not LOG_PATH.exists():
        return go.Figure()
    df = pd.read_csv(LOG_PATH, parse_dates=["timestamp"])
    funding_rows = df[df["event_type"] == "funding"].copy()
    if funding_rows.empty:
        return go.Figure()
    funding_rows = funding_rows.sort_values("timestamp")
    funding_rows["cumulative"] = funding_rows["amount_usd"].astype(float).cumsum()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=funding_rows["timestamp"],
        y=funding_rows["cumulative"],
        mode="lines+markers",
        name="Cumulative Funding",
        line=dict(color="#00c896", width=2),
        fill="tozeroy",
        fillcolor="rgba(0,200,150,0.1)",
    ))
    fig.update_layout(
        title="Cumulative Funding Collected (USD)",
        xaxis_title="Time",
        yaxis_title="USD",
        height=300,
        margin=dict(l=0, r=0, t=40, b=0),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


# ── Auto-refresh ──────────────────────────────────────────────────────────────

st.title("ARB_bot — Funding Rate Arbitrage")
refresh_s = st.sidebar.slider("Auto-refresh (seconds)", 30, 300, 60, step=30)
if st.sidebar.button("Refresh Now"):
    st.rerun()

# Trading mode indicator
mode = TRADING_MODE
if mode == "live":
    st.sidebar.error("🔴 LIVE TRADING — real orders will be placed")
    st.sidebar.markdown("**Balances:**")
    try:
        bals = live_trader.get_balances()
        for ex, bal in bals.items():
            st.sidebar.caption(f"{ex}: ${bal:,.2f}" if isinstance(bal, float) else f"{ex}: {bal}")
    except Exception as e:
        st.sidebar.caption(f"Balance fetch error: {e}")
else:
    st.sidebar.success("🟢 PAPER TRADING — no real orders")

now_str = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
st.caption(f"Binance x OKX x Bybit  |  Mode: **{mode.upper()}**  |  Last updated: {now_str}")

# ── Fetch data ────────────────────────────────────────────────────────────────

with st.spinner("Fetching live data..."):
    opps = scan()
    live_data = get_live_data()
    sim = load_sim()

# ── Metric cards ──────────────────────────────────────────────────────────────

open_pairs = sim.open_pairs()
closed_pairs = sim.closed_pairs()

total_funding = sum(p.funding_collected for p in open_pairs + closed_pairs)
total_fees = sum(p.fees_paid for p in open_pairs + closed_pairs)

total_net = 0.0
for p in open_pairs:
    bd = live_data.get(p.base, {})
    sp = bd.get(p.short_exchange, {}).get("mark_price", p.short_entry_price)
    lp = bd.get(p.long_exchange, {}).get("mark_price", p.long_entry_price)
    total_net += p.net_pnl(sp, lp)
for p in closed_pairs:
    sp = p.short_exit_price or p.short_entry_price
    lp = p.long_exit_price or p.long_entry_price
    total_net += p.net_pnl(sp, lp)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Net P&L (USD)", f"${total_net:+,.4f}")
m2.metric("Open Pairs", len(open_pairs))
m3.metric("Funding Collected", f"${total_funding:,.4f}")
m4.metric("Total Fees Paid", f"${total_fees:,.4f}")

st.divider()

# ── Scanner + Positions ───────────────────────────────────────────────────────

col_scan, col_pos = st.columns([3, 2])

with col_scan:
    st.subheader("Top Arb Spreads")
    if opps:
        scan_df = pd.DataFrame([{
            "Base": o["base"],
            "Short On": o["short_exchange"],
            "Short Rate/8h": f"{o['short_rate']*100:+.4f}%",
            "Short Next": format_time_until(o["short_next_funding"]),
            "Long On": o["long_exchange"],
            "Long Rate/8h": f"{o['long_rate']*100:+.4f}%",
            "Long Next": format_time_until(o["long_next_funding"]),
            "Spread/8h": f"{o['spread']*100:+.4f}%",
            "Capital APR": f"{o['annual_capital_yield']*100:+.2f}%",
            "Beats Fees": "✓" if o["spread"] > ROUND_TRIP_FEE else "",
        } for o in opps])
        st.dataframe(scan_df, use_container_width=True, hide_index=True, height=420)
    else:
        st.info("No cross-exchange spreads found.")

with col_pos:
    st.subheader("Open Positions")
    risk_results = check_all(sim, live_data)
    risk_by_id = {r["pair_id"]: r for r in risk_results}

    if open_pairs:
        pos_rows = []
        for p in open_pairs:
            bd = live_data.get(p.base, {})
            sp = bd.get(p.short_exchange, {}).get("mark_price", p.short_entry_price)
            lp = bd.get(p.long_exchange, {}).get("mark_price", p.long_entry_price)
            r = risk_by_id.get(p.pair_id, {})
            level = r.get("level", ALERT_OK)
            icon = {ALERT_OK: "", ALERT_DRIFT: "⚠", ALERT_CRITICAL: "🔴", ALERT_STOPLOSS: "🛑"}.get(level, "")
            pos_rows.append({
                "": icon,
                "ID": p.pair_id,
                "Base": p.base,
                "Short": p.short_exchange,
                "Long": p.long_exchange,
                "Size": f"${p.size_usd:,.0f}",
                "Drift": f"{r.get('drift_pct', 0)*100:.3f}%",
                "Funding": f"${p.funding_collected:+.4f}",
                "Price PnL": f"${p.price_pnl(sp, lp):+.4f}",
                "Net PnL": f"${p.net_pnl(sp, lp):+.4f}",
            })
        st.dataframe(pd.DataFrame(pos_rows), use_container_width=True, hide_index=True, height=420)
    else:
        st.info("No open positions.")

st.divider()

# ── Risk Alerts ───────────────────────────────────────────────────────────────

alerts = [r for r in risk_results if r["level"] != ALERT_OK]
if alerts:
    st.subheader("Risk Alerts")
    for r in alerts:
        msg = f"**{r['pair_id']} — {r['base']}**  |  " + "  |  ".join(r["alerts"])
        if r["level"] == ALERT_STOPLOSS:
            st.error(msg)
        elif r["level"] == ALERT_CRITICAL:
            st.warning(msg)
        else:
            st.info(msg)
    st.divider()

# ── P&L Chart ─────────────────────────────────────────────────────────────────

st.subheader("Cumulative P&L")
st.plotly_chart(build_pnl_chart(), use_container_width=True)

st.divider()

# ── Controls ──────────────────────────────────────────────────────────────────

st.subheader("Controls")
ctrl1, ctrl2, ctrl3 = st.columns(3)

# Open pair
with ctrl1:
    st.markdown("**Open Arb Pair**")
    st.caption(f"Max size: ${TOTAL_CAPITAL * MAX_POSITION_PCT:,.0f}  |  "
               f"Stop-loss: {STOP_LOSS_PCT*100:.0f}%  |  "
               f"Min drift alert: {DRIFT_WARNING_PCT*100:.1f}%")
    if opps:
        bases = [o["base"] for o in opps]
        selected_base = st.selectbox("Base asset", bases, key="open_base")
        match = next(o for o in opps if o["base"] == selected_base)
        st.caption(
            f"SHORT {match['short_exchange']} {match['short_rate']*100:+.4f}%  |  "
            f"LONG {match['long_exchange']} {match['long_rate']*100:+.4f}%  |  "
            f"Spread: {match['spread']*100:+.4f}%/8h"
        )
        size_usd = st.number_input("Size per leg (USDT)", min_value=10.0, value=1000.0, step=100.0, key="open_size")
        btn_label = "Open Pair (LIVE)" if mode == "live" else "Open Pair (Paper)"
        if st.button(btn_label, type="primary"):
            allowed, reason = validate_open(match["spread"], size_usd, sim)
            if not allowed:
                st.error(f"Risk block: {reason}")
            elif mode == "live":
                try:
                    live_trader.open_live_pair(
                        base=match["base"], size_usd=size_usd,
                        short_exchange=match["short_exchange"],
                        short_price=match["short_price"], short_rate=match["short_rate"],
                        long_exchange=match["long_exchange"],
                        long_price=match["long_price"], long_rate=match["long_rate"],
                    )
                    st.success(f"LIVE: Opened {match['base']} arb pair (${size_usd:,.0f}/leg)")
                    st.rerun()
                except Exception as e:
                    st.error(f"Order failed: {e}")
            else:
                sim.open_pair(
                    base=match["base"], size_usd=size_usd,
                    short_exchange=match["short_exchange"],
                    short_price=match["short_price"], short_rate=match["short_rate"],
                    long_exchange=match["long_exchange"],
                    long_price=match["long_price"], long_rate=match["long_rate"],
                )
                st.success(f"Paper: Opened {match['base']} arb pair (${size_usd:,.0f}/leg)")
                st.rerun()

# Apply funding (paper) / Sync funding (live)
with ctrl2:
    if mode == "live":
        st.markdown("**Sync Live Funding**")
        st.caption("Pull actual funding payments received from each exchange.")
        live_open = live_trader.get_live_positions()
        if st.button("Sync Funding", disabled=len(live_open) == 0):
            try:
                summary = live_trader.sync_funding()
                if not summary:
                    st.info("No open live pairs to sync.")
                else:
                    total = sum(s["net"] for s in summary.values())
                    st.success(f"Synced {len(summary)} pair(s). Total net funding: ${total:+.4f}")
                    for pid, s in summary.items():
                        st.caption(f"{pid}: short ${s['short_funding']:+.4f}  "
                                   f"long ${s['long_funding']:+.4f}  →  net ${s['net']:+.4f}")
            except Exception as e:
                st.error(f"Sync failed: {e}")
    else:
        st.markdown("**Apply Funding Payment**")
        st.caption("Simulate one 8h funding settlement at current live rates.")
        if st.button("Apply Funding", disabled=len(open_pairs) == 0):
            payments = sim.apply_funding(live_data)
            total_payment = sum(payments.values())
            st.success(f"Applied funding to {len(payments)} pair(s).  Net: ${total_payment:+.4f}")
            st.rerun()

# Close pair
with ctrl3:
    st.markdown("**Close Pair**")
    if open_pairs:
        pair_ids = [p.pair_id for p in open_pairs]
        selected_pid = st.selectbox("Pair ID", pair_ids, key="close_pid")
        pair_to_close = sim.pairs[selected_pid]
        bd = live_data.get(pair_to_close.base, {})
        close_sp = bd.get(pair_to_close.short_exchange, {}).get("mark_price", pair_to_close.short_entry_price)
        close_lp = bd.get(pair_to_close.long_exchange, {}).get("mark_price", pair_to_close.long_entry_price)
        r = risk_by_id.get(selected_pid, {})
        st.caption(
            f"{pair_to_close.base}  |  "
            f"Drift: {r.get('drift_pct', 0)*100:.3f}%  |  "
            f"Net PnL: ${pair_to_close.net_pnl(close_sp, close_lp):+.4f}"
        )
        btn_label = "Close Pair (LIVE)" if mode == "live" else "Close Pair (Paper)"
        if st.button(btn_label, type="secondary"):
            if mode == "live":
                try:
                    realized = live_trader.close_live_pair(selected_pid, close_sp, close_lp)
                    st.success(f"LIVE: Closed {selected_pid}.  Approx P&L: ${realized:+.4f}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Close failed: {e}")
            else:
                realized = sim.close_pair(selected_pid, close_sp, close_lp)
                st.success(f"Paper: Closed {selected_pid}.  Realized: ${realized:+.4f}")
                st.rerun()
    else:
        st.info("No open pairs to close.")

# ── Auto-refresh ──────────────────────────────────────────────────────────────
time.sleep(refresh_s)
st.rerun()
