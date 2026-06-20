import argparse
import uuid

from src.auth.jwt_handler import generate_token

def main() -> None:
    parser = argparse.ArgumentParser(description="Day 3-4 — Generate Mock JWT Token")
    parser.add_argument("--role", required=True, choices=["manager", "staff"], help="User RBAC Role level")
    parser.add_argument("--department", required=True, choices=["HR", "Sales"], help="User RBAC Department")
    parser.add_argument("--user-id", default="", help="Optional specific user ID (generates random UUID if empty)")

    args = parser.parse_args()

    user_id = args.user_id if args.user_id else f"emp_{str(uuid.uuid4())[:8]}"
    
    token = generate_token(
        user_id=user_id,
        role=args.role,
        department=args.department
    )
    
    print("\n🔑 Mock token generated successfully for:")
    print(f"  User ID    : {user_id}")
    print(f"  Department : {args.department}")
    print(f"  Role       : {args.role}")
    print("\nToken string (include in Authorization: Bearer <token>):")
    print(f"{token}\n")

if __name__ == "__main__":
    main()
