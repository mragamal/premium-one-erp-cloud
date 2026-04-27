import sqlite3

def check():
    conn = sqlite3.connect('erp.db')
    conn.row_factory = sqlite3.Row
    
    print("--- Advances with missing employees ---")
    rows = conn.execute("""
        SELECT ea.id, ea.employee_id, ea.advance_no, ea.status 
        FROM employee_advances ea 
        WHERE ea.employee_id NOT IN (SELECT id FROM employees)
    """).fetchall()
    for r in rows:
        print(dict(r))
        
    print("\n--- Journal Lines Details ---")
    rows = conn.execute("""
        SELECT * FROM journal_lines WHERE id IN (13307, 13308)
    """).fetchall()
    for r in rows:
        print(dict(r))
        
    print("\n--- Journal Lines Schema ---")
    print(conn.execute("SELECT sql FROM sqlite_master WHERE name='journal_lines'").fetchone()[0])
    
    print("\n--- Trial Balance Check ---")
    account_code = '1020503'
    sql = """
        SELECT SUM(debit) as total_debit, SUM(credit) as total_credit
        FROM journal_lines l
        JOIN journal_entries j ON j.id = l.journal_id
        WHERE j.status = 'posted' AND l.account_code = ?
    """
    row = conn.execute(sql, (account_code,)).fetchone()
    print(dict(row))
        
    conn.close()

if __name__ == "__main__":
    check()
