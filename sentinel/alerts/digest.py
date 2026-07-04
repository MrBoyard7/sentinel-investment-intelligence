"""
Alert composition.

This module turns a list of stored `Item` rows into human-readable
messages and decides which channel(s) each alert type goes out on:

  - Immediate alerts (single high-priority item): email + Slack + SMS
  - Daily digest (all new items in the last day): email + Slack summary
  - Weekly digest (all new items in the last week): email + Slack summary

It is deliberately separate from `sentinel.storage.database` (which only
knows how to read/write rows) and from `sentinel.pipeline` (which decides
*when* to call these functions, e.g. on a schedule).
"""

from __future__ import annotations

from sentinel.alerts.email_alert import send_email
from sentinel.alerts.slack_alert import send_slack_message
from sentinel.alerts.sms_alert import send_sms
from sentinel.storage.models import Item

SENTIMENT_EMOJI = {"Positive": "🟢", "Negative": "🔴", "Neutral": "⚪"}


def send_immediate_alert(item: Item) -> None:
    emoji = SENTIMENT_EMOJI.get(item.sentiment, "⚪")
    subject = f"[Sentinel] Score {item.score}/5 — {item.title[:80]}"

    text_body = (
        f"{emoji} Score {item.score}/5 | {item.sentiment} | {item.category}\n"
        f"Source: {item.source_name}\n\n"
        f"{item.summary}\n\n"
        f"Why it matters: {item.why_it_matters}\n"
        f"Recommended action: {item.recommended_action}\n\n"
        f"Link: {item.url}"
    )
    html_body = f"""
    <h2>{emoji} Score {item.score}/5 — {item.sentiment}</h2>
    <p><strong>{item.title}</strong><br>
    <em>{item.source_name} · {item.category}</em></p>
    <p>{item.summary}</p>
    <p><strong>Why it matters:</strong> {item.why_it_matters}</p>
    <p><strong>Recommended action:</strong> {item.recommended_action}</p>
    <p><a href="{item.url}">Read the source</a></p>
    """

    send_email(subject=subject, body_html=html_body, body_text=text_body)
    send_slack_message(text_body)

    if item.score >= 5:
        send_sms(f"Sentinel ALERT ({item.score}/5): {item.title[:120]} — {item.url}")


def send_digest(items: list[Item], digest_type: str) -> None:
    if not items:
        return

    period_label = "Daily" if digest_type == "daily" else "Weekly"
    subject = f"[Sentinel] {period_label} Digest — {len(items)} new item(s)"

    sorted_items = sorted(items, key=lambda i: i.score, reverse=True)

    text_lines = [f"{period_label} digest — {len(items)} new item(s)\n"]
    html_rows = []
    for item in sorted_items:
        emoji = SENTIMENT_EMOJI.get(item.sentiment, "⚪")
        text_lines.append(
            f"- [{item.score}/5 {emoji}] {item.title} ({item.source_name}) — {item.url}"
        )
        html_rows.append(
            f"<tr><td>{item.score}/5 {emoji}</td><td>{item.category}</td>"
            f"<td><a href='{item.url}'>{item.title}</a></td>"
            f"<td>{item.source_name}</td></tr>"
        )

    text_body = "\n".join(text_lines)
    html_body = f"""
    <h2>{period_label} Digest — {len(items)} new item(s)</h2>
    <table border="1" cellpadding="6" cellspacing="0">
      <tr><th>Score</th><th>Category</th><th>Headline</th><th>Source</th></tr>
      {''.join(html_rows)}
    </table>
    """

    send_email(subject=subject, body_html=html_body, body_text=text_body)
    send_slack_message(
        f"*{period_label} Digest* — {len(items)} new item(s). Check your email/dashboard."
    )
