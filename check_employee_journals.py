
import sqlite3
import os

db_path = "erp.db"
if not os.path.exists(db_path):
    print(f"DB not found at {db_path}")
else:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT j.entry_no, j.entry_date, j.description, l.account_code, l.debit, l.credit, l.partner_id, e.name as employee_name
        FROM journal_lines l
        JOIN journal_entries j ON j.id = l.journal_id
        LEFT JOIN employees e ON e.id = l.partner_id
        WHERE l.partner_type = 'employee'
    """).fetchall()
    for row in rows:
        print(f"{row['entry_no']} | {row['entry_date']} | {row['employee_name']} | DR: {row['debit']} | CR: {row['credit']} | {row['description']}")
    conn.close()
