"""Seeds a user's account with a few short, original German texts for local dev/demo use.

Run as a module so `app` resolves on sys.path:

    uv run python -m scripts.seed_articles <email>

The target user must already exist (register it first through the app). Idempotent: skips
any text whose title already exists for that user.
"""

import argparse
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models import Article, User
from app.schemas.article import ArticleCreate
from app.services.article_service import create_article

SEED_DATA_DIR = Path(__file__).parent / "seed_data"

# "intended_level" is our own rough label for later difficulty-heuristic evaluation — never an
# official CEFR assessment (see docs/blueprint.md section 8/14). It isn't persisted anywhere yet
# because the difficulty heuristic is a separate, future step; it lives here until that step
# gives it a real home.
SEED_ARTICLES = [
    {
        "title": "Samstag auf dem Markt in Nürnberg",
        "file": "markt_nuernberg.txt",
        "intended_level": "A2",
    },
    {
        "title": "Die Stadt baut neue Radwege",
        "file": "radwege_stadt.txt",
        "intended_level": "B1",
    },
    {
        "title": "Homeoffice oder Büro?",
        "file": "homeoffice_debatte.txt",
        "intended_level": "B2",
    },
]


def seed_articles_for_user(db: Session, user: User) -> None:
    for entry in SEED_ARTICLES:
        existing = db.scalar(
            select(Article).where(Article.user_id == user.id, Article.title == entry["title"])
        )
        if existing is not None:
            print(f"Skipping (already exists): {entry['title']}")
            continue

        text = (SEED_DATA_DIR / entry["file"]).read_text(encoding="utf-8").strip()
        create_article(db, user, ArticleCreate(title=entry["title"], original_text=text))
        print(f"Seeded ({entry['intended_level']}, internal label only): {entry['title']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed short German texts for an existing user.")
    parser.add_argument("email", help="Email of an existing, already-registered user.")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == args.email.strip().lower()))
        if user is None:
            print(
                f"No user found with email {args.email!r}. Register that account first.",
                file=sys.stderr,
            )
            sys.exit(1)
        seed_articles_for_user(db, user)
    finally:
        db.close()


if __name__ == "__main__":
    main()
