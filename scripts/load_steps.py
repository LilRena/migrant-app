"""
Load step templates from data/steps_demo.json into the database.
Safe to run multiple times: updates existing rows, inserts new ones.

Upsert logic: for each step in the JSON we look for an existing StepTemplate
row where (country_code, order) matches. country_code can be NULL, so we use
SQLAlchemy's .is_(None) filter which generates "IS NULL" instead of "= NULL"
(the latter never matches anything in SQL). If a row is found we overwrite its
fields; if not found we insert a new row.

All steps are validated BEFORE any database writes: if any step fails
validation, nothing is written to the database.

Run from the project root:
    python -m scripts.load_steps
"""
import json
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from app.db import SessionLocal
from app.models.steps import StepTemplate

STEPS_FILE = Path(__file__).parent.parent / "data" / "steps_demo.json"


def validate_step_data(data: dict, index: int) -> None:
    """Raise ValueError with a clear message if step data is invalid."""
    deadline_type = data.get("deadline_type")
    deadline_days = data.get("deadline_days")
    if deadline_type != "none":
        if deadline_days is None or not isinstance(deadline_days, int) or deadline_days <= 0:
            raise ValueError(
                f"Шаг {index + 1} (order={data.get('order')}, title='{data.get('title')}'): "
                f"deadline_days обязателен и должен быть положительным целым числом, "
                f"когда deadline_type='{deadline_type}'"
            )


def main():
    if not STEPS_FILE.exists():
        print(f"ERROR: {STEPS_FILE} not found.", file=sys.stderr)
        sys.exit(1)

    steps = json.loads(STEPS_FILE.read_text(encoding="utf-8"))

    # validate everything before touching the database
    errors = []
    for i, data in enumerate(steps):
        try:
            validate_step_data(data, i)
        except ValueError as e:
            errors.append(str(e))

    if errors:
        print("Ошибки валидации — ничего не записано в базу:", file=sys.stderr)
        for e in errors:
            print(f"  {e}", file=sys.stderr)
        sys.exit(1)

    db = SessionLocal()
    try:
        inserted = updated = 0
        for data in steps:
            country_code = data.get("country_code")
            order = data["order"]

            # find by (country_code, order) — handles NULL correctly
            q = db.query(StepTemplate).filter(StepTemplate.order == order)
            if country_code is None:
                q = q.filter(StepTemplate.country_code.is_(None))
            else:
                q = q.filter(StepTemplate.country_code == country_code)

            existing = q.first()
            if existing:
                for key, value in data.items():
                    setattr(existing, key, value)
                updated += 1
            else:
                db.add(StepTemplate(**data))
                inserted += 1

        db.commit()
        print(f"Done: {inserted} inserted, {updated} updated.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
