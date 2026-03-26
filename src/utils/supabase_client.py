"""
Supabase client initialization for MedSync.
Provides a singleton Supabase client for the entire application.
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()


class SupabaseClientError(Exception):
    """Custom exception for Supabase client errors."""
    pass


def get_supabase_client() -> Client:
    """
    Create and return a Supabase client instance.

    Reads SUPABASE_URL and SUPABASE_SECRET_KEY from environment variables.

    Returns:
        Client: Initialized Supabase client

    Raises:
        SupabaseClientError: If required environment variables are missing
    """
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SECRET_KEY")

    if not supabase_url:
        raise SupabaseClientError(
            "SUPABASE_URL environment variable is not set. "
            "Please add it to your .env file."
        )

    if not supabase_key:
        raise SupabaseClientError(
            "SUPABASE_SECRET_KEY environment variable is not set. "
            "Please add it to your .env file."
        )

    try:
        client = create_client(supabase_url, supabase_key)
        return client
    except Exception as e:
        raise SupabaseClientError(f"Failed to create Supabase client: {str(e)}")


# Singleton instance - created once and reused
_supabase_client: Client = None


def get_client() -> Client:
    """
    Get the singleton Supabase client instance.

    Creates the client on first call, then returns the cached instance.

    Returns:
        Client: The Supabase client instance
    """
    global _supabase_client

    if _supabase_client is None:
        _supabase_client = get_supabase_client()

    return _supabase_client


def reset_client():
    """
    Reset the singleton client instance.
    Useful for testing or reconnecting with new credentials.
    """
    global _supabase_client
    _supabase_client = None


def test_connection():
    """
    Test the Supabase connection by querying the users table.
    Prints connection status and row count.
    """
    print("=" * 50)
    print("MEDSYNC - Supabase Connection Test")
    print("=" * 50)

    try:
        print("\n[1] Loading environment variables...")
        supabase_url = os.getenv("SUPABASE_URL")
        print(f"    SUPABASE_URL: {supabase_url[:30]}..." if supabase_url else "    SUPABASE_URL: NOT SET")

        print("\n[2] Creating Supabase client...")
        client = get_client()
        print("    Client created successfully!")

        print("\n[3] Querying 'users' table...")
        result = client.table('users').select('*').execute()

        row_count = len(result.data) if result.data else 0
        print(f"    Query successful!")
        print(f"    Rows in 'users' table: {row_count}")

        print("\n" + "=" * 50)
        print("CONNECTION TEST PASSED!")
        print("=" * 50)
        return True

    except SupabaseClientError as e:
        print(f"\n[ERROR] Client error: {e}")
        print("\nCONNECTION TEST FAILED!")
        return False

    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        print("\nCONNECTION TEST FAILED!")
        return False


# Run test when this file is executed directly
if __name__ == "__main__":
    test_connection()
