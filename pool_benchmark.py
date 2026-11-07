
from time import perf_counter
from mysql.connector import pooling
from db import dbconfig

def benchmark(reset_session, label):
    print(f"\n===== {label} =====")

    pool = pooling.MySQLConnectionPool(
        pool_name=f"benchmark_{label.lower()}",
        pool_size=2,
        pool_reset_session=reset_session,
        **dbconfig
    )

    for i in range(5):
        start = perf_counter()

        conn = pool.get_connection()
        acquired = perf_counter()

        cursor = conn.cursor()
        created = perf_counter()

        cursor.execute("SELECT 1")
        executed = perf_counter()

        cursor.fetchone()
        fetched = perf_counter()

        cursor.close()
        cursor_closed = perf_counter()

        conn.close()
        returned = perf_counter()

        print(
            f"Test {i+1}: "
            f"Acquire={(acquired-start)*1000:.2f} ms | "
            f"Cursor={(created-acquired)*1000:.2f} ms | "
            f"Query={(executed-created)*1000:.2f} ms | "
            f"Fetch={(fetched-executed)*1000:.2f} ms | "
            f"Return={(returned-cursor_closed)*1000:.2f} ms | "
            f"Total={(returned-start)*1000:.2f} ms"
        )

benchmark(True, "RESET_ENABLED")
benchmark(False, "RESET_DISABLED")
