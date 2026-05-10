import os
import requests


class TelegramNotifier:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        self.enabled = bool(self.token and self.chat_id)

    def send(self, message: str):
        if not self.enabled:
            return
        try:
            requests.post(
                f"https://api.telegram.org/bot{self.token}/sendMessage",
                json={"chat_id": self.chat_id, "text": message, "parse_mode": "HTML"},
                timeout=5,
            )
        except Exception:
            pass  # notifications are best-effort, never crash the bot

    def opened(self, pair_id: str, base: str, short_ex: str, long_ex: str,
               size_usd: float, spread_pct: float):
        self.send(
            f"<b>OPENED</b> {pair_id}\n"
            f"Asset: <b>{base}</b>\n"
            f"SHORT {short_ex} / LONG {long_ex}\n"
            f"Size: ${size_usd:,.0f}/leg\n"
            f"Spread: {spread_pct:+.4f}%/8h"
        )

    def closed(self, pair_id: str, base: str, realized_pnl: float):
        sign = "+" if realized_pnl >= 0 else ""
        self.send(
            f"<b>CLOSED</b> {pair_id} — {base}\n"
            f"Realized P&L: <b>{sign}${realized_pnl:.4f}</b>"
        )

    def funding(self, pair_id: str, base: str, amount: float):
        sign = "+" if amount >= 0 else ""
        self.send(
            f"<b>FUNDING</b> {pair_id} — {base}\n"
            f"Net payment: <b>{sign}${amount:.4f}</b>"
        )

    def risk_alert(self, pair_id: str, base: str, level: str, detail: str):
        icons = {"drift_warning": "⚠️", "drift_critical": "🔴", "stop_loss": "🛑"}
        icon = icons.get(level, "")
        self.send(f"{icon} <b>RISK ALERT</b> {pair_id} — {base}\n{detail}")

    def error(self, context: str, message: str):
        self.send(f"🔥 <b>ERROR</b> [{context}]\n{message}")
