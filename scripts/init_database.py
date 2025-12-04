#!/usr/bin/env python3
"""
Script to initialize the database schema.

Creates all tables defined in the database models.

Usage:
    python scripts/init_database.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text

from bugbridge.database.connection import get_engine, _engine
from bugbridge.database.models import Base


async def init_database() -> None:
    """
    Initialize the database by creating all tables.
    """
    # Clear cached engine to pick up new DATABASE_URL
    import bugbridge.database.connection as conn_module
    conn_module._engine = None
    
    engine = get_engine()
    
    try:
        print("🔄 Creating database tables...")
        
        # Create all tables
        async with engine.begin() as conn:
            # Drop existing tables if they exist (for development)
            # Comment this out in production!
            await conn.run_sync(Base.metadata.drop_all)
            print("   ✓ Dropped existing tables (if any)")
            
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
            print("   ✓ Created all tables")
        
        print("\n✅ Database initialized successfully!")
        print("\n📋 Created tables:")
        for table_name in Base.metadata.tables.keys():
            print(f"   - {table_name}")
        
    except Exception as e:
        print(f"\n❌ Error initializing database: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        await engine.dispose()


def main():
    """Main entry point."""
    asyncio.run(init_database())


if __name__ == "__main__":
    main()

