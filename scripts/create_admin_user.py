#!/usr/bin/env python3
"""
Script to create an admin user for BugBridge dashboard.

Usage:
    python scripts/create_admin_user.py
    python scripts/create_admin_user.py --username admin --password admin123 --email admin@bugbridge.local

Note: Make sure to activate the virtual environment first:
    source venv/bin/activate
"""

import asyncio
import argparse
import sys
from pathlib import Path
from datetime import datetime
from uuid import uuid4

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Check if we're in a virtual environment or if dependencies are installed
try:
    import sqlalchemy
except ImportError:
    print("❌ Error: Required packages not found.")
    print("\n💡 Please activate the virtual environment first:")
    print("   source venv/bin/activate")
    print("\n   Or install dependencies:")
    print("   pip install -r requirements.txt")
    sys.exit(1)

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bugbridge.database.connection import get_session
from bugbridge.database.models import User
from bugbridge.api.routes.auth import get_password_hash


async def create_admin_user(
    username: str = "admin",
    password: str = "admin123",
    email: str = "admin@bugbridge.local",
) -> None:
    """
    Create an admin user in the database.
    
    Args:
        username: Username for the admin user
        password: Plain text password (will be hashed)
        email: Email address for the admin user
    """
    async for session in get_session():
        try:
            # Check if user already exists
            query = select(User).where(User.username == username)
            result = await session.execute(query)
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                print(f"✅ User '{username}' already exists!")
                print(f"   Email: {existing_user.email}")
                print(f"   Role: {existing_user.role}")
                print(f"   Active: {existing_user.is_active}")
                print("\n💡 You can use these credentials to login:")
                print(f"   Username: {username}")
                print(f"   Password: (use the password you set when creating this user)")
                return
            
            # Create new admin user
            admin_user = User(
                id=uuid4(),
                username=username,
                email=email,
                password_hash=get_password_hash(password),
                role="admin",
                is_active=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            )
            
            session.add(admin_user)
            await session.commit()
            
            print("✅ Admin user created successfully!")
            print("\n📋 Login Credentials:")
            print(f"   Username: {username}")
            print(f"   Password: {password}")
            print(f"   Email: {email}")
            print(f"   Role: admin")
            print("\n💡 You can now login at http://localhost:3000/login")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Error creating admin user: {e}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            await session.close()
        break


async def list_users() -> None:
    """List all users in the database."""
    async for session in get_session():
        try:
            query = select(User)
            result = await session.execute(query)
            users = result.scalars().all()
            
            if not users:
                print("ℹ️  No users found in database")
                return
            
            print(f"📋 Found {len(users)} user(s):\n")
            for user in users:
                print(f"   Username: {user.username}")
                print(f"   Email: {user.email}")
                print(f"   Role: {user.role}")
                print(f"   Active: {user.is_active}")
                print(f"   Created: {user.created_at}")
                print()
                
        except Exception as e:
            print(f"❌ Error listing users: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await session.close()
        break


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Create admin user for BugBridge dashboard")
    parser.add_argument("--username", default="admin", help="Username (default: admin)")
    parser.add_argument("--password", default="admin123", help="Password (default: admin123)")
    parser.add_argument("--email", default="admin@bugbridge.local", help="Email (default: admin@bugbridge.local)")
    parser.add_argument("--list", action="store_true", help="List all existing users")
    
    args = parser.parse_args()
    
    if args.list:
        asyncio.run(list_users())
    else:
        asyncio.run(create_admin_user(
            username=args.username,
            password=args.password,
            email=args.email,
        ))


if __name__ == "__main__":
    main()

