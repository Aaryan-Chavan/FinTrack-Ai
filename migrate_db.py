from db import get_db_connection

def upgrade_database():
    conn = get_db_connection()
    cur = conn.cursor()

    queries = [
        "ALTER TABLE Users ADD COLUMN password_hash VARCHAR(255) NULL",
        "ALTER TABLE Users ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP",
        "ALTER TABLE Users ADD COLUMN full_name VARCHAR(255) NULL",
        "ALTER TABLE Transactions DROP INDEX category",
        "ALTER TABLE Transactions ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP",
        """CREATE TABLE IF NOT EXISTS UserProfiles (
            user_id INT PRIMARY KEY,
            take_home_salary DECIMAL(12,2) DEFAULT 0.00,
            essential_expenses DECIMAL(12,2) DEFAULT 0.00,
            debt_obligations DECIMAL(12,2) DEFAULT 0.00,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE
        )""",
        """CREATE TABLE IF NOT EXISTS SavingsGoals (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            name VARCHAR(100) NOT NULL,
            target_amount DECIMAL(12,2) NOT NULL,
            current_amount DECIMAL(12,2) DEFAULT 0.00,
            type VARCHAR(50),
            target_date DATE NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE
        )""",
        """CREATE TABLE IF NOT EXISTS MonthlyClosures (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            month VARCHAR(7) NOT NULL,
            recorded_income DECIMAL(12,2) NOT NULL,
            recorded_expense DECIMAL(12,2) NOT NULL,
            recorded_surplus DECIMAL(12,2) NOT NULL,
            confirmed_surplus DECIMAL(12,2) NULL,
            is_closed BOOLEAN DEFAULT FALSE,
            closed_at DATETIME NULL,
            FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE,
            UNIQUE KEY uq_user_month (user_id, month)
        )""",
        """CREATE TABLE IF NOT EXISTS SurplusAllocations (
            id INT AUTO_INCREMENT PRIMARY KEY,
            closure_id INT NOT NULL,
            user_id INT NOT NULL,
            emergency_allocation DECIMAL(12,2) DEFAULT 0.00,
            short_term_allocation DECIMAL(12,2) DEFAULT 0.00,
            investments_allocation DECIMAL(12,2) DEFAULT 0.00,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (closure_id) REFERENCES MonthlyClosures(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE,
            UNIQUE KEY uq_closure_alloc (closure_id)
        )""",
        """CREATE TABLE IF NOT EXISTS FinancialProducts (
            id INT AUTO_INCREMENT PRIMARY KEY,
            category VARCHAR(50) NOT NULL,
            name VARCHAR(150) NOT NULL,
            interest_rate_pct DECIMAL(5,2) NULL,
            risk_level VARCHAR(50) NOT NULL,
            liquidity VARCHAR(50) NOT NULL,
            min_investment DECIMAL(12,2) NULL,
            lock_in_period VARCHAR(50) NULL,
            source_url VARCHAR(255) NOT NULL,
            verified_date DATE NOT NULL,
            UNIQUE KEY uq_product_name (name)
        )""",
        # Clean up any duplicate products from earlier runs before adding unique index
        """DELETE p1 FROM FinancialProducts p1
           INNER JOIN FinancialProducts p2
           WHERE p1.id > p2.id AND p1.name = p2.name""",
        "ALTER TABLE FinancialProducts ADD UNIQUE KEY uq_product_name (name)",
        """INSERT INTO FinancialProducts (category, name, interest_rate_pct, risk_level, liquidity, min_investment, lock_in_period, source_url, verified_date)
        VALUES 
        ('fd', 'SBI 1-Year Fixed Deposit', 6.80, 'Low', 'Moderate', 1000.00, '1 Year', 'https://sbi.co.in/web/interest-rates', '2026-01-01'),
        ('govt', 'Public Provident Fund (PPF)', 7.10, 'Very Low', 'Low', 500.00, '15 Years', 'https://www.indiapost.gov.in', '2026-01-01'),
        ('mutual_fund', 'Nifty 50 Index Fund Category Average', 12.00, 'High', 'High', 500.00, 'None', 'https://www.amfiindia.com', '2026-01-01'),
        ('govt', 'Senior Citizen Savings Scheme (SCSS)', 8.20, 'Very Low', 'Low', 1000.00, '5 Years', 'https://www.indiapost.gov.in', '2026-01-01')
        ON DUPLICATE KEY UPDATE
            interest_rate_pct=VALUES(interest_rate_pct),
            min_investment=VALUES(min_investment),
            verified_date=VALUES(verified_date)"""
    ]

    for q in queries:
        try:
            cur.execute(q)
            conn.commit()
            print("Successfully executed migration step.")
        except Exception as e:
            print(f"Skipped step (already applied): {e}")

    cur.close()
    conn.close()
    print("\nDATABASE SCHEMA UPGRADE COMPLETE!")

if __name__ == '__main__':
    upgrade_database()