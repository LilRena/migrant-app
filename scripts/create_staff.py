"""
Create a staff account. Run from the project root:
    python -m scripts.create_staff
"""
import sys
from dotenv import load_dotenv

load_dotenv()

from app.db import SessionLocal
from app.models.user import User, UserRole
from app.security import hash_password


def main():
    email = input("Email сотрудника: ").strip()
    full_name = input("Имя сотрудника: ").strip()
    password = input("Пароль: ").strip()

    if not email or not password or not full_name:
        print("Все поля обязательны.")
        sys.exit(1)

    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == email).first():
            print(f"Пользователь {email} уже существует.")
            sys.exit(1)
        user = User(
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
            role=UserRole.staff,
        )
        db.add(user)
        db.commit()
        print(f"Сотрудник {email} создан.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
