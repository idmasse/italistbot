import pandas as pd
import sqlite3

def create_products_db(csv_path: str, db_path: str):
    # load the csv into a dataframe
    products_df = pd.read_csv(csv_path, low_memory=False)
    
    # create or connect to the SQLite db
    conn = sqlite3.connect(db_path)
    
    # write the dataframe to a table named products
    products_df.to_sql('products', conn, if_exists='replace', index=False)
    
    # create an index on the 'id' column for faster lookups
    conn.execute("CREATE INDEX IF NOT EXISTS idx_skuid ON products (id);")
    conn.commit()
    
    # verify that data has been written.
    sample_query = conn.execute("SELECT * FROM products LIMIT 5;").fetchall()
    print('Sample rows from the products table:')
    for row in sample_query:
        print(row)
    
    conn.close()

def get_product_url(sku: str, db_path: str = 'italist.db') -> str:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT link FROM products WHERE id = ?", (sku,))
    result = cursor.fetchone()
    conn.close()
    
    return result[0] if result else None

if __name__ == "__main__":
    create_products_db('italist.csv', 'italist.db')
