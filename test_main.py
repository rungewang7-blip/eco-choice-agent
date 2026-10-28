from fastapi import FastAPI
import sqlite3

app = FastAPI()

def test_db_connection():
    conn = sqlite3.connect("eco.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY, name TEXT)")
    cursor.execute("INSERT INTO test (name) VALUES (?)", ("test_data",))
    conn.commit()
    conn.close()

test_db_connection()

carbon_factors = {
    "red_meat": 19.2,
    "chicken": 6.9,
    "public_transport": 0.04,
    "petrol_car": 0.21
}

@app.get("/factors")
def get_carbon_factors():
    return carbon_factors
