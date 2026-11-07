
from time import perf_counter
from db import get_db_connection

def measure(label, operation):
    start = perf_counter()
    result = operation()
    elapsed = (perf_counter() - start) * 1000
    print(f"{label}: {elapsed:.2f} ms")
    return result

for i in range(10):
    print(f"\n--- Test {i + 1} ---")

    start = perf_counter()

    conn = get_db_connection()
    acquired = perf_counter()
    print(f"Connection acquisition: {(acquired - start) * 1000:.2f} ms")

    cursor = conn.cursor()
    cursor_created = perf_counter()
    print(f"Cursor creation: {(cursor_created - acquired) * 1000:.2f} ms")

    cursor.execute("SELECT 1")
    executed = perf_counter()
    print(f"Query execution: {(executed - cursor_created) * 1000:.2f} ms")

    cursor.fetchone()
    fetched = perf_counter()
    print(f"Fetch: {(fetched - executed) * 1000:.2f} ms")

    cursor.close()
    cursor_closed = perf_counter()
    print(f"Cursor close: {(cursor_closed - fetched) * 1000:.2f} ms")

    conn.close()
    returned = perf_counter()
    print(f"Connection return/reset: {(returned - cursor_closed) * 1000:.2f} ms")

    print(f"Total: {(returned - start) * 1000:.2f} ms")
