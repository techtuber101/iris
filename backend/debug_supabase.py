import asyncio
import os
from supabase import create_async_client

async def test_supabase():
    print("Testing Supabase client creation...")

    try:
        # Get the actual environment variables
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

        print(f"1. Environment variables:")
        print(f"   SUPABASE_URL: {supabase_url}")
        print(f"   SUPABASE_SERVICE_ROLE_KEY: {supabase_key[:20]}..." if supabase_key else "   None")

        print("2. create_async_client function:")
        print(f"   Type: {type(create_async_client)}")

        print("3. Creating client...")
        client = await create_async_client(supabase_url, supabase_key)
        print(f"   Client type: {type(client)}")

        print("4. Checking client methods:")
        methods = [x for x in dir(client) if not x.startswith('_')]
        print(f"   Methods: {methods}")

        print("5. Checking for table method:")
        print(f"   Has table method: {hasattr(client, 'table')}")

        if hasattr(client, 'table'):
            print("6. Testing table method:")
            try:
                table_obj = client.table('threads')
                print(f"   Table object type: {type(table_obj)}")
                print(f"   Table methods: {[x for x in dir(table_obj) if not x.startswith('_')]}")
                print(f"   Has select method: {hasattr(table_obj, 'select')}")
            except Exception as e:
                print(f"   Error calling table: {e}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_supabase())
