"""
Flask dashboard application.

Two things are served from here:

  1. `/` - a server-rendered page (Jinja) so the dashboard has a fast,
     working first paint even with JavaScript disabled.
  2. `/api/items` and `/api/stats` - JSON endpoints that dashboard.js polls
     to apply filters client-side without a full page reload.

This keeps the dashboard usable as a static-ish page while still feeling
like a live tool, without pulling in a full frontend build toolchain -
an appropriate trade-off for a monitoring dashboard whose primary job is
showing tabular data clearly.
"""

from __future__ import annotations

from flask import Flask, jsonify, render_template, request

from sentinel.settings import load_watchlist
from sentinel.storage import database


def create_app() -> Flask:
    app = Flask(__name__)

    @app.route("/")
    def index():
        database.init_db()
        watchlist = load_watchlist()
        items = database.get_items(limit=200)
        stats = database.get_stats()
        return render_template(
            "dashboard.html",
            items=items,
            stats=stats,
            theme=watchlist.get("theme", {}),
        )

    @app.route("/api/items")
    def api_items():
        min_score = request.args.get("min_score", type=int)
        category = request.args.get("category") or None
        sentiment = request.args.get("sentiment") or None
        items = database.get_items(
            min_score=min_score, category=category, sentiment=sentiment
        )
        return jsonify(items)

    @app.route("/api/stats")
    def api_stats():
        return jsonify(database.get_stats())

    return app


if __name__ == "__main__":
    from sentinel.settings import settings

    create_app().run(
        host=settings.dashboard_host, port=settings.dashboard_port, debug=True
    )
