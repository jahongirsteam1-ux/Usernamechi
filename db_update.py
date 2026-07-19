import asyncio
import aiosqlite

async def main():
    async with aiosqlite.connect('saas.db') as db:
        try: 
            await db.execute('ALTER TABLE users ADD COLUMN is_premium INTEGER DEFAULT 0')
        except Exception as e: 
            print("is_premium exists or error:", e)
            
        try: 
            await db.execute('ALTER TABLE users ADD COLUMN premium_until TEXT')
        except Exception as e: 
            print("premium_until exists or error:", e)
            
        await db.execute('''
        CREATE TABLE IF NOT EXISTS keyword_subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            user_id INTEGER, 
            keyword TEXT, 
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        try: 
            await db.execute('ALTER TABLE listings ADD COLUMN is_private INTEGER DEFAULT 0')
        except Exception as e: 
            print("is_private exists or error:", e)
            
        await db.commit()

asyncio.run(main())
