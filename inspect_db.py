import sqlite3, os

db_path = r"C:\Users\Siviglino\Desktop\Pro superenalotto\superenalotto.db"
conn = sqlite3.connect(db_path)
c = conn.cursor()

# Tables
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in c.fetchall()]
print("Tables:", tables)

# Count rows
for t in tables:
    c.execute(f"SELECT COUNT(*) FROM [{t}]")
    print(f"  {t}: {c.fetchone()[0]} rows")

# Last 3 draws
c.execute("SELECT * FROM estrazioni ORDER BY data DESC LIMIT 3")
print("\nLast 3 draws:")
for r in c.fetchall():
    print(f"  {r}")

# Last 5 giocate
c.execute("SELECT * FROM giocate ORDER BY id DESC LIMIT 5")
print("\nLast 5 giocate:")
for r in c.fetchall():
    print(f"  {r}")

# Check for any draws with future dates
from datetime import datetime
today = datetime.now().strftime("%Y-%m-%d")
c.execute("SELECT data FROM estrazioni WHERE data > ? ORDER BY data", (today,))
future = c.fetchall()
print(f"\nFuture draws: {len(future)}")
for r in future:
    print(f"  {r[0]}")

# Check for duplicate dates
c.execute("SELECT data, COUNT(*) as cnt FROM estrazioni GROUP BY data HAVING cnt > 1")
dups = c.fetchall()
print(f"\nDuplicate dates: {len(dups)}")
for r in dups:
    print(f"  {r[0]}: {r[1]} times")

# Check date range
c.execute("SELECT MIN(data), MAX(data) FROM estrazioni")
row = c.fetchone()
print(f"\nDate range: {row[0]} to {row[1]}")

# Check for missing columns in giocate
c.execute("PRAGMA table_info(giocate)")
print("\nGiocate columns:")
for r in c.fetchall():
    print(f"  {r}")

conn.close()