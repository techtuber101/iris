import asyncio
from services.supabase import db

async def test_db_connection():
    try:
        print("Initializing database...")
        await db.initialize()
        print("Getting client...")
        client = await db.get_client()
        print(f"Client type: {type(client)}")
        print(f"Client has table method: {hasattr(client, 'table')}")

        if hasattr(client, 'table'):
            print("Testing table method...")
            result = await client.table('threads').select('*').limit(1).execute()
            print(f"Query successful: {result}")
        else:
            print("Client does not have table method")
            print(f"Client methods: {[x for x in dir(client) if not x.startswith('_')]}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_db_connection())
