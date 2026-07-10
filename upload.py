import asyncio
import asyncpg
import pandas as pd
import os

async def upload_csv_to_neon():

    # Reading CSV
    file_path = 'faq_data.csv'
    if not os.path.exists(file_path):
        print(f"File {file_path} not found.")
        return
    
    df = pd.read_csv(file_path)

    # Connecting database
    db_url = os.getenv('DATABASE_URL')

    print("Connecting to Neon database...")
    conn = await asyncpg.connect(db_url)

    try:
        # Table creation
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS binance_faq (
                id SERIAL PRIMARY KEY,
                question TEXT,
                answer TEXT
            )
        ''')
        
        # Clean & paste
        await conn.execute('TRUNCATE binance_faq')
        data_to_insert = [tuple(x) for x in df[['question', 'answer']].values]

        await conn.executemany('''
            INSERT INTO binance_faq (question, answer) 
            VALUES ($1, $2)
        ''', data_to_insert)

        print(f"Successfully uploaded {len(data_to_insert)} strings.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(upload_csv_to_neon())
