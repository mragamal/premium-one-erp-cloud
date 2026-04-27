from html import escape
from urllib.parse import quote

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from db import get_conn
from i18n import get_lang
from layout import render_page
from modules.accounting.employee_advances_statement import advance_statement_ui
from modules.hr.employees import ensure_employees_table, safe, to_float

router = APIRouter()
BASE_ROUTE = "/ui/accounting/employee-advances"
LEGACY_ROUTE = "/ui/hr/advances"


def money(value):
    try:
        return f"{float(value or 0):,.2f}"
    except Exception:
        return "0.00"


def tr(request: Request, en: str, ar: str) -> str:
    return ar if get_lang(request) == "ar" else en


def with_lang(request: Request, path: str) -> str:
    lang = get_lang(request)
    separator = "&" if "?" in path else "?"
    return f"{path}{separator}lang={lang}" if lang == "ar" else path


def status_label(request: Request, status: str) -> str:
    key = safe(status).lower() or "active"
    labels = {
        "active": tr(request, "Active", "نشطة"),
        "open": tr(request, "Open", "مفتوحة"),
        "closed": tr(request, "Closed", "مقفلة"),
        "cancelled": tr(request, "Cancelled", "ملغية"),
    }
    return labels.get(key, safe(status) or tr(request, "Active", "نشطة"))


def can_edit_or_delete_advance(row) -> bool:
    if not row:
        return False
    if safe(row.get("journal_line_id")).strip():
        return False
    return safe(row.get("status")).lower() in ("active", "open")


def ensure_column(conn, table_name, column_name, alter_sql):
    cols = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    names = [c["name"] for c in cols]
    if column_name not in names:
        conn.execute(alter_sql)


def ensure_advances_tables():
    ensure_employees_table()
    conn = get_conn()

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS employee_advances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            advance_no TEXT UNIQUE,
            advance_date TEXT,
            employee_id INTEGER NOT NULL,
            amount REAL DEFAULT 0,
            installment_amount REAL DEFAULT 0,
            start_month INTEGER,
            start_year INTEGER,
            notes TEXT,
            status TEXT DEFAULT 'active',
            journal_line_id INTEGER,
            is_opening_balance INTEGER DEFAULT 0,
            paid_before_start REAL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS employee_advance_deductions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            advance_id INTEGER NOT NULL,
            payroll_run_id INTEGER NOT NULL,
            payroll_line_id INTEGER,
            deduction_month INTEGER,
            deduction_year INTEGER,
            amount REAL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_advance_deduction_unique
        ON employee_advance_deductions (advance_id, payroll_run_id, payroll_line_id)
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS employee_advance_installments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            advance_id INTEGER NOT NULL,
            installment_month INTEGER,
            installment_year INTEGER,
            planned_amount REAL DEFAULT 0,
            paid_amount REAL DEFAULT 0,
            status TEXT DEFAULT 'pending',
            is_deferred INTEGER DEFAULT 0,
            deferred_reason TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # Table to track deferral requests (exceptions)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS employee_advance_deferrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            advance_id INTEGER NOT NULL,
            installment_id INTEGER,
            original_month INTEGER,
            original_year INTEGER,
            deferred_to_month INTEGER,
            deferred_to_year INTEGER,
            amount REAL DEFAULT 0,
            reason TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    ensure_column(conn, "employee_advances", "advance_no", "ALTER TABLE employee_advances ADD COLUMN advance_no TEXT")
    ensure_column(conn, "employee_advances", "advance_date", "ALTER TABLE employee_advances ADD COLUMN advance_date TEXT")
    ensure_column(conn, "employee_advances", "employee_id", "ALTER TABLE employee_advances ADD COLUMN employee_id INTEGER")
    ensure_column(conn, "employee_advances", "amount", "ALTER TABLE employee_advances ADD COLUMN amount REAL DEFAULT 0")
    ensure_column(conn, "employee_advances", "installment_amount", "ALTER TABLE employee_advances ADD COLUMN installment_amount REAL DEFAULT 0")
    ensure_column(conn, "employee_advances", "start_month", "ALTER TABLE employee_advances ADD COLUMN start_month INTEGER")
    ensure_column(conn, "employee_advances", "start_year", "ALTER TABLE employee_advances ADD COLUMN start_year INTEGER")
    ensure_column(conn, "employee_advances", "notes", "ALTER TABLE employee_advances ADD COLUMN notes TEXT")
    ensure_column(conn, "employee_advances", "status", "ALTER TABLE employee_advances ADD COLUMN status TEXT DEFAULT 'active'")
    ensure_column(conn, "employee_advances", "journal_line_id", "ALTER TABLE employee_advances ADD COLUMN journal_line_id INTEGER")
    ensure_column(conn, "employee_advances", "created_at", "ALTER TABLE employee_advances ADD COLUMN created_at TEXT DEFAULT CURRENT_TIMESTAMP")
    ensure_column(conn, "employee_advances", "is_opening_balance", "ALTER TABLE employee_advances ADD COLUMN is_opening_balance INTEGER DEFAULT 0")
    ensure_column(conn, "employee_advances", "paid_before_start", "ALTER TABLE employee_advances ADD COLUMN paid_before_start REAL DEFAULT 0")

    ensure_column(conn, "employee_advance_deductions", "advance_id", "ALTER TABLE employee_advance_deductions ADD COLUMN advance_id INTEGER")
    ensure_column(conn, "employee_advance_deductions", "payroll_run_id", "ALTER TABLE employee_advance_deductions ADD COLUMN payroll_run_id INTEGER")
    ensure_column(conn, "employee_advance_deductions", "payroll_line_id", "ALTER TABLE employee_advance_deductions ADD COLUMN payroll_line_id INTEGER")
    ensure_column(conn, "employee_advance_deductions", "deduction_month", "ALTER TABLE employee_advance_deductions ADD COLUMN deduction_month INTEGER")
    ensure_column(conn, "employee_advance_deductions", "deduction_year", "ALTER TABLE employee_advance_deductions ADD COLUMN deduction_year INTEGER")
    ensure_column(conn, "employee_advance_deductions", "amount", "ALTER TABLE employee_advance_deductions ADD COLUMN amount REAL DEFAULT 0")
    ensure_column(conn, "employee_advance_deductions", "created_at", "ALTER TABLE employee_advance_deductions ADD COLUMN created_at TEXT DEFAULT CURRENT_TIMESTAMP")

    conn.commit()
    conn.close()


def regenerate_installment_schedule(conn, advance_id):
    advance = conn.execute("SELECT * FROM employee_advances WHERE id = ?", (advance_id,)).fetchone()
    if not advance:
        return

    paid_total = advance_paid_amount(conn, advance_id)
    # For opening balance advances, subtract the amount already paid before system start
    paid_before_start = float(advance["paid_before_start"] or 0)
    remaining = float(advance["amount"] or 0) - paid_total - paid_before_start
    remaining = max(remaining, 0)

    # Delete pending installments (keep paid/deferred ones intact)
    conn.execute("DELETE FROM employee_advance_installments WHERE advance_id = ? AND status = 'pending'", (advance_id,))

    if remaining <= 0:
        return

    installment_amount = float(advance["installment_amount"] or 0)
    if installment_amount <= 0:
        installment_amount = remaining  # One shot

    m = int(advance["start_month"] or 1)
    y = int(advance["start_year"] or 2024)

    while remaining > 0.001:
        # Skip months that already have a paid deduction
        paid_in_period = conn.execute("""
            SELECT SUM(amount) as total FROM employee_advance_deductions
            WHERE advance_id = ? AND deduction_month = ? AND deduction_year = ?
        """, (advance_id, m, y)).fetchone()

        if paid_in_period and paid_in_period["total"] and paid_in_period["total"] > 0:
            m += 1
            if m > 12:
                m = 1
                y += 1
            continue

        # Skip months that already have a pending installment (from deferral)
        existing = conn.execute("""
            SELECT id FROM employee_advance_installments
            WHERE advance_id = ? AND installment_month = ? AND installment_year = ? AND status = 'pending'
        """, (advance_id, m, y)).fetchone()

        if existing:
            # Already has a pending installment this month (e.g. deferred here), skip
            m += 1
            if m > 12:
                m = 1
                y += 1
            continue

        amt = min(remaining, installment_amount)
        conn.execute("""
            INSERT INTO employee_advance_installments (advance_id, installment_month, installment_year, planned_amount, status)
            VALUES (?, ?, ?, ?, 'pending')
        """, (advance_id, m, y, amt))

        remaining -= amt
        m += 1
        if m > 12:
            m = 1
            y += 1


def defer_installment(conn, advance_id, installment_id, reason=""):
    """
    Defer a pending installment to the next available month.
    Records the deferral in employee_advance_deferrals and rebuilds the schedule.
    """
    inst = conn.execute(
        "SELECT * FROM employee_advance_installments WHERE id = ? AND advance_id = ? AND status = 'pending'",
        (installment_id, advance_id)
    ).fetchone()
    if not inst:
        return False, "Installment not found or already paid."

    orig_month = int(inst["installment_month"] or 0)
    orig_year = int(inst["installment_year"] or 0)
    amount = float(inst["planned_amount"] or 0)

    # Find next available month (no pending/paid installment)
    nm = orig_month + 1
    ny = orig_year
    if nm > 12:
        nm = 1
        ny += 1

    # Keep advancing until we find a free month
    for _ in range(120):  # max 10 years safety
        occupied = conn.execute("""
            SELECT id FROM employee_advance_installments
            WHERE advance_id = ? AND installment_month = ? AND installment_year = ?
        """, (advance_id, nm, ny)).fetchone()
        if not occupied:
            break
        nm += 1
        if nm > 12:
            nm = 1
            ny += 1

    # Mark original as deferred
    conn.execute(
        "UPDATE employee_advance_installments SET status = 'deferred', is_deferred = 1, deferred_reason = ? WHERE id = ?",
        (reason, installment_id)
    )

    # Insert deferred installment in new month
    conn.execute("""
        INSERT INTO employee_advance_installments
            (advance_id, installment_month, installment_year, planned_amount, status, is_deferred, deferred_reason)
        VALUES (?, ?, ?, ?, 'pending', 1, ?)
    """, (advance_id, nm, ny, amount, reason))

    # Record deferral history
    conn.execute("""
        INSERT INTO employee_advance_deferrals
            (advance_id, installment_id, original_month, original_year, deferred_to_month, deferred_to_year, amount, reason)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (advance_id, installment_id, orig_month, orig_year, nm, ny, amount, reason))

    return True, f"Deferred from {orig_month:02d}/{orig_year} to {nm:02d}/{ny}"



    ensure_advances_tables()
    conn = get_conn()
    row = conn.execute(
        """
        SELECT advance_no
        FROM employee_advances
        WHERE COALESCE(advance_no, '') <> ''
        ORDER BY id DESC
        LIMIT 1
        """
    ).fetchone()
    conn.close()
    last = safe(row["advance_no"]) if row else ""
    if not last:
        return "ADV-0001"
    try:
        num = int(last.split("-")[-1])
    except Exception:
        num = 0
    return f"ADV-{num + 1:04d}"


def next_advance_no():
    ensure_advances_tables()
    conn = get_conn()
    row = conn.execute(
        """
        SELECT advance_no
        FROM employee_advances
        WHERE COALESCE(advance_no, '') <> ''
        ORDER BY id DESC
        LIMIT 1
        """
    ).fetchone()
    conn.close()
    last = safe(row["advance_no"]) if row else ""
    if not last:
        return "ADV-0001"
    try:
        num = int(last.split("-")[-1])
    except Exception:
        num = 0
    return f"ADV-{num + 1:04d}"


def employee_options_html(selected_id=""):
    ensure_employees_table()
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT id, code, name
        FROM employees
        WHERE COALESCE(is_active, 1) = 1
        ORDER BY code, name
        """
    ).fetchall()
    conn.close()

    html = '<option value="">-- Select Employee --</option>'
    selected_text = safe(selected_id)
    for row in rows:
        rid = str(row["id"])
        sel = "selected" if rid == selected_text else ""
        label = f"{safe(row['code'])} - {safe(row['name'])}" if safe(row["code"]) else safe(row["name"])
        html += f'<option value="{rid}" {sel}>{escape(label)}</option>'
    return html


def advance_paid_amount(conn, advance_id):
    row = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) AS total FROM employee_advance_deductions WHERE advance_id = ?",
        (advance_id,),
    ).fetchone()
    return float(row["total"] or 0)


def advance_remaining_amount(conn, advance_row):
    return max(float(advance_row["amount"] or 0) - advance_paid_amount(conn, advance_row["id"]), 0)


def period_key(month, year):
    return (int(year or 0) * 100) + int(month or 0)


def is_due_in_period(start_month, start_year, payroll_month, payroll_year):
    if int(start_month or 0) <= 0 or int(start_year or 0) <= 0:
        return True
    return period_key(start_month, start_year) <= period_key(payroll_month, payroll_year)


def get_employee_due_advances(conn, employee_id, payroll_month, payroll_year):
    # Primary source: scheduled installments for this payroll period.
    rows = conn.execute(
        """
        SELECT ei.*, ea.advance_no, ea.employee_id
        FROM employee_advance_installments ei
        JOIN employee_advances ea ON ea.id = ei.advance_id
        WHERE ea.employee_id = ?
          AND ei.installment_month = ?
          AND ei.installment_year = ?
          AND ei.status = 'pending'
          AND LOWER(COALESCE(ea.status, 'active')) IN ('active', 'open')
        """,
        (employee_id, payroll_month, payroll_year),
    ).fetchall()

    due_rows = []
    for row in rows:
        due_rows.append(
            {
                "id": int(row["advance_id"]),
                "installment_id": int(row["id"]),
                "advance_no": safe(row["advance_no"]),
                "due_amount": float(row["planned_amount"] or 0),
            }
        )

    # Backward-compatibility fallback:
    # Some historical advances may not have generated installment rows.
    # In that case, derive due amount from advance setup so payroll still deducts.
    if due_rows:
        return due_rows

    legacy_advances = conn.execute(
        """
        SELECT *
        FROM employee_advances
        WHERE employee_id = ?
          AND LOWER(COALESCE(status, 'active')) IN ('active', 'open')
        ORDER BY id
        """,
        (employee_id,),
    ).fetchall()

    for advance in legacy_advances:
        if not is_due_in_period(
            advance["start_month"],
            advance["start_year"],
            payroll_month,
            payroll_year,
        ):
            continue

        remaining = advance_remaining_amount(conn, advance)
        if remaining <= 0:
            continue

        installment = float(advance["installment_amount"] or 0)
        due_amount = installment if installment > 0 else remaining
        due_amount = min(due_amount, remaining)
        if due_amount <= 0:
            continue

        due_rows.append(
            {
                "id": int(advance["id"]),
                "installment_id": None,
                "advance_no": safe(advance["advance_no"]),
                "due_amount": due_amount,
            }
        )

    return due_rows


def get_employee_due_advance_total(conn, employee_id, payroll_month, payroll_year):
    return sum(row["due_amount"] for row in get_employee_due_advances(conn, employee_id, payroll_month, payroll_year))


def sync_advance_status(conn, advance_id):
    row = conn.execute("SELECT * FROM employee_advances WHERE id = ? LIMIT 1", (advance_id,)).fetchone()
    if not row:
        return
    remaining = advance_remaining_amount(conn, row)
    status = "closed" if remaining <= 0.0001 else "active"
    conn.execute("UPDATE employee_advances SET status = ? WHERE id = ?", (status, advance_id))


def allocate_payroll_advance_deductions(conn, run_id):
    run = conn.execute("SELECT * FROM payroll_runs WHERE id = ? LIMIT 1", (run_id,)).fetchone()
    if not run:
        return

    payroll_month = int(run["payroll_month"] or 0)
    payroll_year = int(run["payroll_year"] or 0)
    lines = conn.execute(
        """
        SELECT *
        FROM payroll_lines
        WHERE payroll_run_id = ?
        ORDER BY id
        """,
        (run_id,),
    ).fetchall()

    conn.execute("DELETE FROM employee_advance_deductions WHERE payroll_run_id = ?", (run_id,))

    for line in lines:
        remaining_to_allocate = float(line["advance_deduction"] or 0)
        if remaining_to_allocate <= 0:
            continue

        due_advances = get_employee_due_advances(conn, line["employee_id"], payroll_month, payroll_year)
        for advance in due_advances:
            if remaining_to_allocate <= 0:
                break
            allocation = min(remaining_to_allocate, float(advance["due_amount"] or 0))
            if allocation <= 0:
                continue
            conn.execute(
                """
                INSERT INTO employee_advance_deductions (
                    advance_id, payroll_run_id, payroll_line_id, deduction_month, deduction_year, amount
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    advance["id"],
                    run_id,
                    line["id"],
                    payroll_month,
                    payroll_year,
                    allocation,
                ),
            )
            remaining_to_allocate -= allocation
            sync_advance_status(conn, advance["id"])

        if remaining_to_allocate > 0:
            for advance in due_advances:
                if remaining_to_allocate <= 0:
                    break
                row = conn.execute("SELECT * FROM employee_advances WHERE id = ? LIMIT 1", (advance["id"],)).fetchone()
                if not row:
                    continue
                remaining_balance = advance_remaining_amount(conn, row)
                extra_allocation = min(remaining_to_allocate, remaining_balance)
                if extra_allocation <= 0:
                    continue
                exists = conn.execute(
                    """
                    SELECT id, amount
                    FROM employee_advance_deductions
                    WHERE advance_id = ? AND payroll_run_id = ? AND payroll_line_id = ?
                    LIMIT 1
                    """,
                    (advance["id"], run_id, line["id"]),
                ).fetchone()
                if exists:
                    conn.execute(
                        "UPDATE employee_advance_deductions SET amount = ? WHERE id = ?",
                        (float(exists["amount"] or 0) + extra_allocation, exists["id"]),
                    )
                else:
                    conn.execute(
                        """
                        INSERT INTO employee_advance_deductions (
                            advance_id, payroll_run_id, payroll_line_id, deduction_month, deduction_year, amount
                        )
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            advance["id"],
                            run_id,
                            line["id"],
                            payroll_month,
                            payroll_year,
                            extra_allocation,
                        ),
                    )
                remaining_to_allocate -= extra_allocation
                sync_advance_status(conn, advance["id"])

    advance_ids = conn.execute("SELECT id FROM employee_advances").fetchall()
    for row in advance_ids:
        sync_advance_status(conn, row["id"])


ensure_advances_tables()


@router.get(LEGACY_ROUTE)
def legacy_advances_redirect(request: Request):
    return RedirectResponse(with_lang(request, BASE_ROUTE), status_code=302)


@router.get(f"{BASE_ROUTE}/sync-from-journal")
def advances_sync_from_journal(request: Request):
    conn = get_conn()
    try:
        # Find journal lines for employees in accounts that look like advances
        # which are NOT already in employee_advances
        # We look for debit lines (new advances or opening balances)
        lines = conn.execute("""
            SELECT l.id, l.partner_id, l.debit, l.credit, j.entry_date, j.entry_no, j.description, l.line_description, a.name as account_name
            FROM journal_lines l
            JOIN journal_entries j ON j.id = l.journal_id
            JOIN accounts a ON a.code = l.account_code
            WHERE l.partner_type = 'employee'
              AND l.debit > 0
              AND (
                a.code IN (SELECT value FROM accounting_settings WHERE key = 'employee_advance_account')
                OR a.name LIKE '%سلف%'
                OR a.name LIKE '%قرض%'
                OR a.name LIKE '%advance%'
                OR a.name LIKE '%loan%'
              )
              AND l.id NOT IN (SELECT journal_line_id FROM employee_advances WHERE journal_line_id IS NOT NULL)
              AND j.status = 'posted'
        """).fetchall()

        count = 0
        for l in lines:
            # Create advance
            # We need a unique advance_no for each
            row = conn.execute("SELECT advance_no FROM employee_advances ORDER BY id DESC LIMIT 1").fetchone()
            last = safe(row["advance_no"]) if row else ""
            if not last:
                adv_no = f"ADV-S-{l['id']:04d}"
            else:
                try:
                    num = int(last.split("-")[-1])
                    adv_no = f"ADV-{num + 1 + count:04d}"
                except:
                    adv_no = f"ADV-S-{l['id']:04d}"

            desc = l["line_description"] or l["description"] or f"Synced from {l['entry_no']}"

            conn.execute("""
                INSERT INTO employee_advances (
                    advance_no, advance_date, employee_id, amount, installment_amount, notes, status, journal_line_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                adv_no, l["entry_date"], l["partner_id"], l["debit"], 0, desc, 'open', l["id"]
            ))
            count += 1
        
        conn.commit()
        msg = tr(request, f"Synced {count} advances from journal.", f"تم مزامنة {count} سلفة من قيود اليومية.")
        return RedirectResponse(with_lang(request, BASE_ROUTE) + f"?msg={quote(msg)}", status_code=302)
    except Exception as e:
        return HTMLResponse(f"Error: {str(e)}", status_code=500)
    finally:
        conn.close()


@router.post(f"{BASE_ROUTE}/{{advance_id}}/mark-disbursed")
def advance_mark_disbursed(request: Request, advance_id: int):
    conn = get_conn()
    conn.execute("UPDATE employee_advances SET status = 'open' WHERE id = ?", (advance_id,))
    conn.commit()
    conn.close()
    msg = tr(request, "Advance marked as disbursed.", "تم تحديد السلفة كمصروفة.")
    return RedirectResponse(with_lang(request, BASE_ROUTE) + f"?msg={quote(msg)}", status_code=302)


@router.get(f"{BASE_ROUTE}/{{advance_id}}/edit", response_class=HTMLResponse)
def advances_edit_ui(request: Request, advance_id: int):
    lang = get_lang(request)
    conn = get_conn()
    advance = conn.execute("SELECT * FROM employee_advances WHERE id = ?", (advance_id,)).fetchone()
    if not advance:
        conn.close()
        return HTMLResponse("Not found", status_code=404)
    
    if not can_edit_or_delete_advance(dict(advance)):
        conn.close()
        return HTMLResponse(
            tr(
                request,
                "Cannot edit this advance after it is linked to journal or closed/cancelled.",
                "لا يمكن تعديل هذه السلفة بعد ربطها بالقيود أو بعد إقفالها/إلغائها.",
            ),
            status_code=400,
        )
    
    is_ob = int(advance["is_opening_balance"] or 0)
    paid_ob_val = float(advance["paid_before_start"] or 0)
    employee_label = f"{safe(advance['employee_id'])}"
    # Get employee name for display
    emp_row = conn.execute("SELECT code, name FROM employees WHERE id = ?", (advance["employee_id"],)).fetchone()
    emp_display = f"{safe(emp_row['code'])} - {safe(emp_row['name'])}" if emp_row else str(advance["employee_id"])

    ob_badge = f' <span class="status-chip blue" style="font-size:11px;">{tr(request, "Opening Balance", "رصيد افتتاحي")}</span>' if is_ob else ""

    html = f"""
    <div class="card">
        <h2>{tr(request, "Edit Installment Schedule", "تعديل طريقة السداد")} — {escape(safe(advance['advance_no']))}{ob_badge}</h2>

        <div style="background:#f9fafb; border-radius:8px; padding:14px; margin-bottom:20px; border:1px solid #e5e7eb;">
            <div style="font-weight:600; color:#6b7280; margin-bottom:10px; font-size:13px;">
                {tr(request, "Advance Info (Read Only)", "بيانات السلفة — للاطلاع فقط")}
            </div>
            <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(200px,1fr)); gap:12px;">
                <div>
                    <div style="font-size:12px;color:#9ca3af;">{tr(request, "Advance No", "رقم السلفة")}</div>
                    <div style="font-weight:600;">{escape(safe(advance['advance_no']))}</div>
                </div>
                <div>
                    <div style="font-size:12px;color:#9ca3af;">{tr(request, "Date", "التاريخ")}</div>
                    <div style="font-weight:600;">{escape(safe(advance['advance_date']))}</div>
                </div>
                <div>
                    <div style="font-size:12px;color:#9ca3af;">{tr(request, "Employee", "الموظف")}</div>
                    <div style="font-weight:600;">{escape(emp_display)}</div>
                </div>
                <div>
                    <div style="font-size:12px;color:#9ca3af;">{tr(request, "Advance Amount", "قيمة السلفة")}</div>
                    <div style="font-weight:600; color:#1d4ed8;">{money(advance['amount'])}</div>
                </div>
                {f'''<div>
                    <div style="font-size:12px;color:#9ca3af;">{tr(request, "Paid Before System", "مسدد قبل النظام")}</div>
                    <div style="font-weight:600; color:#7c3aed;">{money(paid_ob_val)}</div>
                </div>''' if is_ob and paid_ob_val > 0 else ""}
            </div>
        </div>

        <form method="post" action="{with_lang(request, f'{BASE_ROUTE}/{advance_id}/edit')}">
            <input type="hidden" name="advance_date" value="{safe(advance['advance_date'])}">
            <input type="hidden" name="employee_id" value="{advance['employee_id']}">
            <input type="hidden" name="amount" value="{advance['amount']}">
            <input type="hidden" name="is_opening_balance" value="{'1' if is_ob else '0'}">
            <input type="hidden" name="paid_before_start" value="{paid_ob_val}">

            <div style="font-weight:600; color:#374151; margin-bottom:14px;">
                {tr(request, "Payment Schedule Settings", "إعدادات جدول السداد")}
            </div>

            <div class="row">
                <div class="col">
                    <label>{tr(request, "Monthly Installment", "القسط الشهري")}</label>
                    <input type="number" step="0.01" min="0" name="installment_amount" value="{advance['installment_amount']}" required>
                </div>
                <div class="col">
                    <label>{tr(request, "Deduction Start Month", "شهر بداية الخصم")}</label>
                    <input type="number" min="1" max="12" name="start_month" value="{advance['start_month']}" required>
                </div>
            </div>

            <div class="row" style="margin-top:14px;">
                <div class="col">
                    <label>{tr(request, "Deduction Start Year", "سنة بداية الخصم")}</label>
                    <input type="number" min="2020" max="2100" name="start_year" value="{advance['start_year']}" required>
                </div>
                <div class="col">
                    <label>{tr(request, "Notes", "ملاحظات")}</label>
                    <input name="notes" value="{escape(safe(advance['notes']))}">
                </div>
            </div>

            <div style="margin-top:18px;">
                <button class="btn green" type="submit">{tr(request, "Update Schedule", "تحديث جدول السداد")}</button>
                <a class="btn gray" href="{with_lang(request, f'{BASE_ROUTE}/{advance_id}')}">{tr(request, "Back", "رجوع")}</a>
            </div>
        </form>
    </div>
    """
    conn.close()
    return HTMLResponse(render_page(tr(request, "Edit Installment Schedule", "تعديل طريقة السداد"), html, lang, current_path=request.url.path))


@router.post(f"{BASE_ROUTE}/{{advance_id}}/edit")
def advances_update(
    request: Request,
    advance_id: int,
    advance_date: str = Form(""),
    employee_id: int = Form(...),
    amount: str = Form("0"),
    installment_amount: str = Form("0"),
    start_month: int = Form(...),
    start_year: int = Form(...),
    notes: str = Form(""),
    is_opening_balance: str = Form(""),
    paid_before_start: str = Form("0"),
):
    conn = get_conn()
    advance = conn.execute("SELECT status, journal_line_id FROM employee_advances WHERE id = ?", (advance_id,)).fetchone()
    if not advance or not can_edit_or_delete_advance(dict(advance)):
        conn.close()
        return HTMLResponse(
            tr(
                request,
                "Cannot update this advance after it is linked to journal or closed/cancelled.",
                "لا يمكن تحديث هذه السلفة بعد ربطها بالقيود أو بعد إقفالها/إلغائها.",
            ),
            status_code=400,
        )

    is_ob = 1 if is_opening_balance == "1" else 0
    paid_ob = max(to_float(paid_before_start), 0) if is_ob else 0.0

    conn.execute(
        """
        UPDATE employee_advances
        SET advance_date = ?, employee_id = ?, amount = ?, installment_amount = ?,
            start_month = ?, start_year = ?, notes = ?, is_opening_balance = ?, paid_before_start = ?
        WHERE id = ?
        """,
        (
            safe(advance_date),
            int(employee_id),
            to_float(amount),
            max(to_float(installment_amount), 0),
            int(start_month or 0),
            int(start_year or 0),
            safe(notes),
            is_ob,
            paid_ob,
            advance_id
        ),
    )
    regenerate_installment_schedule(conn, advance_id)
    conn.commit()
    conn.close()
    msg = tr(request, "Advance updated successfully.", "تم تحديث السلفة بنجاح.")
    return RedirectResponse(with_lang(request, BASE_ROUTE) + f"?msg={quote(msg)}", status_code=302)


@router.post(f"{BASE_ROUTE}/{{advance_id}}/delete")
def advances_delete(request: Request, advance_id: int):
    conn = get_conn()
    advance = conn.execute("SELECT status, journal_line_id FROM employee_advances WHERE id = ?", (advance_id,)).fetchone()
    if not advance or not can_edit_or_delete_advance(dict(advance)):
        conn.close()
        return HTMLResponse(
            tr(
                request,
                "Cannot delete this advance after it is linked to journal or closed/cancelled.",
                "لا يمكن حذف هذه السلفة بعد ربطها بالقيود أو بعد إقفالها/إلغائها.",
            ),
            status_code=400,
        )

    conn.execute("DELETE FROM employee_advances WHERE id = ?", (advance_id,))
    conn.commit()
    conn.close()
    msg = tr(request, "Advance deleted successfully.", "تم حذف السلفة بنجاح.")
    return RedirectResponse(with_lang(request, BASE_ROUTE) + f"?msg={quote(msg)}", status_code=302)


@router.get(f"{BASE_ROUTE}/statement", response_class=HTMLResponse)
def advance_statement_router(request: Request):
    from modules.accounting.employee_advances_statement import advance_statement_ui
    return advance_statement_ui(request)


@router.get(f"{BASE_ROUTE}/statement", response_class=HTMLResponse)
def advances_statement_route(request: Request):
    return advance_statement_ui(request)


@router.get(BASE_ROUTE, response_class=HTMLResponse)
@router.get(LEGACY_ROUTE, response_class=HTMLResponse)
def advances_list(request: Request):
    ensure_advances_tables()
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT ea.*, e.code AS employee_code, e.name AS employee_name
        FROM employee_advances ea
        LEFT JOIN employees e ON e.id = ea.employee_id
        ORDER BY ea.id DESC
        """
    ).fetchall()
    conn.close()

    msg = safe(request.query_params.get("msg"))
    msg_html = f'<div class="msg success">{escape(msg)}</div>' if msg else ""

    body = ""
    for row in rows:
        local_conn = get_conn()
        paid = advance_paid_amount(local_conn, row["id"])
        balance = max(float(row["amount"] or 0) - paid, 0)
        local_conn.close()
        status_cls = "green" if safe(row["status"]).lower() == "closed" else "orange"
        employee_label = f"{safe(row['employee_code'])} - {safe(row['employee_name'])}" if safe(row["employee_code"]) else safe(row["employee_name"])
        body += f"""
        <tr>
            <td>{escape(safe(row['advance_no']))}</td>
            <td>{escape(safe(row['advance_date']))}</td>
            <td>
                {escape(employee_label)}
                <br>
                <small>
                    <a href="/ui/accounting/partner-ledger?partner_type=employee&partner_id={row['employee_id']}" style="color:blue;text-decoration:none;">
                        {tr(request, "View Statement", "كشف حساب")}
                    </a>
                </small>
            </td>
            <td class="number-cell">{money(row['amount'])}</td>
            <td class="number-cell">{money(row['installment_amount'])}</td>
            <td class="number-cell">{money(paid)}</td>
            <td class="number-cell">{money(balance)}</td>
            <td><span class="status-chip {status_cls}">{escape(status_label(request, safe(row['status'])))}</span></td>
            <td style="white-space:nowrap;">
                <a class="btn blue" href="{with_lang(request, f'{BASE_ROUTE}/{row["id"]}')}">{tr(request, "Open", "فتح")}</a>
            </td>
        </tr>
        """

    if not body:
        body = f"<tr><td colspan='9' style='text-align:center;'>{tr(request, 'No employee advances found.', 'لا توجد سلف موظفين مسجلة.')}</td></tr>"

    lang = get_lang(request)
    html = f"""
    <div class="card">
        {msg_html}
        <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;">
            <h2>{tr(request, "Employee Advances", "سلف الموظفين")}</h2>
            <div style="display:flex;gap:10px;">
                <a class="btn gray" href="{with_lang(request, f'{BASE_ROUTE}/statement')}">
                    {tr(request, "Advances Statement", "كشف حساب السلف")}
                </a>
                <a class="btn blue" href="{with_lang(request, f'{BASE_ROUTE}/sync-from-journal')}">
                    {tr(request, "Sync from Journal", "مزامنة من القيود")}
                </a>
                <a class="btn green" href="{with_lang(request, f'{BASE_ROUTE}/new')}">+ {tr(request, "New Advance", "سلفة جديدة")}</a>
            </div>
        </div>
        <p class="section-note">{tr(request, "Employee advances are tracked separately from custody and can be deducted automatically in payroll.", "سلف الموظفين تُسجل بشكل مستقل عن العهدة، ويتم خصمها تلقائيًا من المرتبات حسب الجدول المستحق.")}</p>
    </div>

    <div class="card">
        <table>
            <tr>
                <th>{tr(request, "Advance No", "رقم السلفة")}</th>
                <th>{tr(request, "Date", "التاريخ")}</th>
                <th>{tr(request, "Employee", "الموظف")}</th>
                <th>{tr(request, "Total", "الإجمالي")}</th>
                <th>{tr(request, "Installment", "القسط")}</th>
                <th>{tr(request, "Deducted", "المخصوم")}</th>
                <th>{tr(request, "Balance", "الرصيد")}</th>
                <th>{tr(request, "Status", "الحالة")}</th>
                <th>{tr(request, "Action", "الإجراء")}</th>
            </tr>
            {body}
        </table>
    </div>
    """
    return HTMLResponse(render_page(tr(request, "Employee Advances", "سلف الموظفين"), html, lang, current_path=request.url.path))


@router.get(f"{LEGACY_ROUTE}/new")
def legacy_advances_new_redirect(request: Request):
    return RedirectResponse(with_lang(request, f"{BASE_ROUTE}/new"), status_code=302)


@router.get(f"{BASE_ROUTE}/new", response_class=HTMLResponse)
def advances_new(request: Request):
    lang = get_lang(request)
    html = f"""
    <div class="card">
        <h2>{tr(request, "New Employee Advance", "سلفة موظف جديدة")}</h2>
        <form method="post" action="{with_lang(request, f'{BASE_ROUTE}/new')}">
            <div class="row">
                <div class="col">
                    <label>{tr(request, "Advance No", "رقم السلفة")}</label>
                    <input name="advance_no" value="{next_advance_no()}" readonly>
                </div>
                <div class="col">
                    <label>{tr(request, "Advance Date", "تاريخ السلفة")}</label>
                    <input type="date" name="advance_date" required>
                </div>
            </div>

            <div class="row" style="margin-top:14px;">
                <div class="col">
                    <label>{tr(request, "Employee", "الموظف")}</label>
                    <select name="employee_id" required>
                        {employee_options_html()}
                    </select>
                </div>
                <div class="col">
                    <label>{tr(request, "Advance Amount", "قيمة السلفة")}</label>
                    <input type="number" step="0.01" min="0" name="amount" required>
                </div>
            </div>

            <div class="row" style="margin-top:14px;">
                <div class="col">
                    <label>{tr(request, "Monthly Installment", "القسط الشهري")}</label>
                    <input type="number" step="0.01" min="0" name="installment_amount" required>
                </div>
                <div class="col">
                    <label>{tr(request, "Deduction Start Month", "شهر بداية الخصم")}</label>
                    <input type="number" min="1" max="12" name="start_month" required>
                </div>
            </div>

            <div class="row" style="margin-top:14px;">
                <div class="col">
                    <label>{tr(request, "Deduction Start Year", "سنة بداية الخصم")}</label>
                    <input type="number" min="2020" max="2100" name="start_year" required>
                </div>
                <div class="col">
                    <label>{tr(request, "Notes", "ملاحظات")}</label>
                    <input name="notes">
                </div>
            </div>

            <div style="margin-top:18px; padding:14px; background:#f0f9ff; border-radius:8px; border:1px solid #bae6fd;">
                <div style="font-weight:600; margin-bottom:10px; color:#0369a1;">
                    {tr(request, "Opening Balance Options", "خيارات الرصيد الافتتاحي")}
                </div>
                <div class="row">
                    <div class="col">
                        <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">
                            <input type="checkbox" name="is_opening_balance" value="1" id="isOpeningBalance"
                                onchange="document.getElementById('openingBalanceFields').style.display=this.checked?'block':'none'">
                            {tr(request, "This is an Opening Balance Advance", "هذه السلفة من الرصيد الافتتاحي")}
                        </label>
                        <small style="color:#6b7280;">
                            {tr(request, "Use this for advances that existed before the system start date.", "استخدم هذا الخيار للسلف التي كانت موجودة قبل بدء استخدام النظام.")}
                        </small>
                    </div>
                </div>
                <div id="openingBalanceFields" style="display:none; margin-top:12px;">
                    <div class="row">
                        <div class="col">
                            <label>{tr(request, "Amount Already Paid (Before System Start)", "المبلغ المسدد قبل بدء النظام")}</label>
                            <input type="number" step="0.01" min="0" name="paid_before_start" value="0">
                            <small style="color:#6b7280;">
                                {tr(request, "This amount will be deducted from the total to calculate remaining installments.", "هذا المبلغ سيُحسم من الإجمالي لحساب الأقساط المتبقية.")}
                            </small>
                        </div>
                    </div>
                </div>
            </div>

            <div style="margin-top:18px;">
                <button class="btn green" type="submit">{tr(request, "Save Advance", "حفظ السلفة")}</button>
                <a class="btn gray" href="{with_lang(request, BASE_ROUTE)}">{tr(request, "Back", "رجوع")}</a>
            </div>
        </form>
    </div>
    """
    return HTMLResponse(render_page(tr(request, "New Employee Advance", "سلفة موظف جديدة"), html, lang, current_path=request.url.path))


@router.post(f"{LEGACY_ROUTE}/new")
@router.post(f"{BASE_ROUTE}/new")
def advances_create(
    request: Request,
    advance_no: str = Form(""),
    advance_date: str = Form(""),
    employee_id: int = Form(...),
    amount: str = Form("0"),
    installment_amount: str = Form("0"),
    start_month: int = Form(...),
    start_year: int = Form(...),
    notes: str = Form(""),
    is_opening_balance: str = Form(""),
    paid_before_start: str = Form("0"),
):
    ensure_advances_tables()
    if to_float(amount) <= 0:
        return RedirectResponse(with_lang(request, BASE_ROUTE) + "&msg=" + quote(tr(request, "Advance amount must be greater than zero.", "قيمة السلفة يجب أن تكون أكبر من صفر.")), status_code=302)

    is_ob = 1 if is_opening_balance == "1" else 0
    paid_ob = max(to_float(paid_before_start), 0) if is_ob else 0.0

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO employee_advances (
            advance_no, advance_date, employee_id, amount, installment_amount,
            start_month, start_year, notes, status, is_opening_balance, paid_before_start
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)
        """,
        (
            safe(advance_no) or next_advance_no(),
            safe(advance_date),
            int(employee_id),
            to_float(amount),
            max(to_float(installment_amount), 0),
            int(start_month or 0),
            int(start_year or 0),
            safe(notes),
            is_ob,
            paid_ob,
        ),
    )
    new_id = cur.lastrowid
    regenerate_installment_schedule(conn, new_id)
    conn.commit()
    conn.close()
    return RedirectResponse(with_lang(request, BASE_ROUTE) + "&msg=" + quote(tr(request, "Employee advance created successfully.", "تم إنشاء سلفة الموظف بنجاح.")), status_code=302)


@router.get(f"{LEGACY_ROUTE}" + "/{advance_id}")
def legacy_advance_open_redirect(request: Request, advance_id: int):
    return RedirectResponse(with_lang(request, f"{BASE_ROUTE}/{advance_id}"), status_code=302)


@router.get(f"{BASE_ROUTE}" + "/{advance_id}", response_class=HTMLResponse)
def advance_open(request: Request, advance_id: int):
    ensure_advances_tables()
    conn = get_conn()
    advance = conn.execute(
        """
        SELECT ea.*, e.code AS employee_code, e.name AS employee_name
        FROM employee_advances ea
        LEFT JOIN employees e ON e.id = ea.employee_id
        WHERE ea.id = ?
        LIMIT 1
        """,
        (advance_id,),
    ).fetchone()
    if not advance:
        conn.close()
        return HTMLResponse(tr(request, "Employee advance not found", "سلفة الموظف غير موجودة"), status_code=404)

    deductions = conn.execute(
        """
        SELECT ead.*, pr.payroll_no, pr.payroll_month, pr.payroll_year
        FROM employee_advance_deductions ead
        LEFT JOIN payroll_runs pr ON pr.id = ead.payroll_run_id
        WHERE ead.advance_id = ?
        ORDER BY ead.id DESC
        """,
        (advance_id,),
    ).fetchall()

    # Installment schedule
    installments = conn.execute(
        """
        SELECT * FROM employee_advance_installments
        WHERE advance_id = ?
        ORDER BY installment_year, installment_month
        """,
        (advance_id,),
    ).fetchall()

    # Deferral history
    deferrals = conn.execute(
        """
        SELECT * FROM employee_advance_deferrals WHERE advance_id = ?
        ORDER BY id DESC
        """,
        (advance_id,),
    ).fetchall()

    paid = advance_paid_amount(conn, advance_id)
    paid_before_start = float(advance["paid_before_start"] or 0)
    balance = max(float(advance["amount"] or 0) - paid - paid_before_start, 0)
    is_ob = int(advance["is_opening_balance"] or 0)
    conn.close()

    deduction_rows = ""
    for row in deductions:
        deduction_rows += f"""
        <tr>
            <td>{escape(safe(row['payroll_no']))}</td>
            <td>{int(row['deduction_month'] or 0):02d}/{row['deduction_year'] or ''}</td>
            <td class="number-cell">{money(row['amount'])}</td>
        </tr>
        """

    if not deduction_rows:
        deduction_rows = f"<tr><td colspan='3' style='text-align:center;'>{tr(request, 'No payroll deductions recorded yet.', 'لا توجد خصومات مرتبات مسجلة على هذه السلفة حتى الآن.')}</td></tr>"

    # Build installment schedule rows
    inst_rows = ""
    is_active = safe(advance["status"]).lower() in ("active", "open")
    for inst in installments:
        st = safe(inst["status"]).lower()
        if st == "paid":
            st_badge = f'<span class="status-chip green">{tr(request, "Paid", "مدفوع")}</span>'
            action_cell = ""
        elif st == "deferred":
            reason_txt = escape(safe(inst["deferred_reason"]))
            st_badge = f'<span class="status-chip orange">{tr(request, "Deferred", "مؤجل")}</span>'
            action_cell = f'<small style="color:#9ca3af;">{reason_txt}</small>'
        else:
            st_badge = f'<span class="status-chip blue">{tr(request, "Pending", "قيد الانتظار")}</span>'
            deferred_label = "🔁 " + tr(request, "Defer", "تأجيل")
            if is_active:
                action_cell = f"""
                <form method="post" action="{with_lang(request, f'{BASE_ROUTE}/{advance_id}/defer-installment')}" style="display:inline-flex;gap:6px;align-items:center;">
                    <input type="hidden" name="installment_id" value="{inst['id']}">
                    <input name="reason" placeholder="{tr(request, 'Reason', 'السبب')}" style="padding:3px 6px;border:1px solid #ddd;border-radius:4px;font-size:12px;width:120px;">
                    <button class="btn orange" type="submit" style="padding:2px 8px;font-size:12px;">{deferred_label}</button>
                </form>
                """
            else:
                action_cell = ""

        deferred_icon = " 🔁" if int(inst["is_deferred"] or 0) and st != "deferred" else ""
        inst_rows += f"""
        <tr>
            <td>{int(inst['installment_month'] or 0):02d}/{inst['installment_year'] or ''}</td>
            <td class="number-cell">{money(inst['planned_amount'])}{deferred_icon}</td>
            <td>{st_badge}</td>
            <td>{action_cell}</td>
        </tr>
        """

    if not inst_rows:
        inst_rows = f"<tr><td colspan='4' style='text-align:center;'>{tr(request, 'No installment schedule generated.', 'لا يوجد جدول أقساط.')}</td></tr>"

    # Deferral history rows
    deferral_rows = ""
    for d in deferrals:
        deferral_rows += f"""
        <tr>
            <td>{int(d['original_month'] or 0):02d}/{d['original_year'] or ''}</td>
            <td>{int(d['deferred_to_month'] or 0):02d}/{d['deferred_to_year'] or ''}</td>
            <td class="number-cell">{money(d['amount'])}</td>
            <td>{escape(safe(d['reason']))}</td>
        </tr>
        """

    opening_balance_badge = ""
    if is_ob:
        opening_balance_badge = f' <span class="status-chip blue" style="font-size:11px;">{tr(request, "Opening Balance", "رصيد افتتاحي")}</span>'

    opening_balance_kpi = ""
    if is_ob and paid_before_start > 0:
        opening_balance_kpi = f"""
        <div class="kpi-card">
            <div class="kpi-label">{tr(request, "Paid Before System", "مدفوع قبل النظام")}</div>
            <div class="kpi-value" style="color:#7c3aed;">{money(paid_before_start)}</div>
        </div>
        """

    employee_label = f"{safe(advance['employee_code'])} - {safe(advance['employee_name'])}" if safe(advance["employee_code"]) else safe(advance["employee_name"])
    status_cls = "green" if safe(advance["status"]).lower() == "closed" else "orange"
    can_modify = can_edit_or_delete_advance(dict(advance))
    lang = get_lang(request)
    html = f"""
    <div class="card">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap;">
            <div>
                <h2>{tr(request, "Employee Advance", "سلفة الموظف")} {escape(safe(advance['advance_no']))}{opening_balance_badge}</h2>
                <p><b>{tr(request, "Employee:", "الموظف:")}</b> {escape(employee_label)}</p>
                <p><b>{tr(request, "Date:", "التاريخ:")}</b> {escape(safe(advance['advance_date']))}</p>
                <p><b>{tr(request, "Deduction Start:", "بداية الخصم:")}</b> {int(advance['start_month'] or 0):02d}/{advance['start_year'] or ''}</p>
                <p><b>{tr(request, "Status:", "الحالة:")}</b> <span class="status-chip {status_cls}">{escape(status_label(request, safe(advance['status'])))}</span></p>
                <p><b>{tr(request, "Notes:", "ملاحظات:")}</b> {escape(safe(advance['notes']))}</p>
            </div>
            <div class="kpi-grid" style="min-width:280px;">
                <div class="kpi-card">
                    <div class="kpi-label">{tr(request, "Advance Total", "إجمالي السلفة")}</div>
                    <div class="kpi-value">{money(advance['amount'])}</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">{tr(request, "Installment", "القسط")}</div>
                    <div class="kpi-value">{money(advance['installment_amount'])}</div>
                </div>
                {opening_balance_kpi}
                <div class="kpi-card">
                    <div class="kpi-label">{tr(request, "Deducted", "المخصوم")}</div>
                    <div class="kpi-value">{money(paid)}</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">{tr(request, "Balance", "الرصيد")}</div>
                    <div class="kpi-value">{money(balance)}</div>
                </div>
            </div>
        </div>
        <div style="margin-top:16px; display:flex; gap:10px;">
            <a class="btn gray" href="{with_lang(request, BASE_ROUTE)}">{tr(request, "Back", "رجوع")}</a>
            {f'<a class="btn green" href="/ui/accounting/cash-payments/new?party_type=employee&employee_id={advance["employee_id"]}&employee_trans_type=advance&advance_id={advance["id"]}&amount={advance["amount"]}">{tr(request, "Disburse Advance", "صرف السلفة")}</a>' if safe(advance["status"]).lower() == "active" else ""}
            {f'<a class="btn orange" href="{with_lang(request, f"{BASE_ROUTE}/{advance["id"]}/edit")}">{tr(request, "Edit", "تعديل")}</a>' if can_modify else ""}
            {f'<form method="post" action="{with_lang(request, f"{BASE_ROUTE}/{advance["id"]}/delete")}" style="display:inline;" onsubmit="return confirm(\'{tr(request, "Are you sure you want to delete this advance?", "هل أنت متأكد من حذف هذه السلفة؟")}\')"><button class="btn red" type="submit">{tr(request, "Delete", "حذف")}</button></form>' if can_modify else ""}
            {f'<form method="post" action="{with_lang(request, f"{BASE_ROUTE}/{advance["id"]}/mark-disbursed")}" style="display:inline;"><button class="btn blue" type="submit">{tr(request, "Mark as Disbursed", "تحديد كمصروفة")}</button></form>' if safe(advance["status"]).lower() == "active" else ""}
        </div>
    </div>

    <div class="card">
        <h3>{tr(request, "Installment Schedule", "جدول الأقساط")}</h3>
        <p style="color:#6b7280;font-size:13px;">{tr(request, "You can defer a pending installment to the next available month.", "يمكنك تأجيل قسط معلق إلى أول شهر متاح.")}</p>
        <table>
            <thead><tr>
                <th>{tr(request, "Month", "الشهر")}</th>
                <th>{tr(request, "Amount", "المبلغ")}</th>
                <th>{tr(request, "Status", "الحالة")}</th>
                <th>{tr(request, "Action", "الإجراء")}</th>
            </tr></thead>
            <tbody>{inst_rows}</tbody>
        </table>
    </div>

    <div class="card">
        <h3>{tr(request, "Deduction Ledger", "ليدجر الخصومات")}</h3>
        <table>
            <tr>
                <th>{tr(request, "Payroll Run", "مسير المرتب")}</th>
                <th>{tr(request, "Period", "الفترة")}</th>
                <th>{tr(request, "Amount", "المبلغ")}</th>
            </tr>
            {deduction_rows}
        </table>
    </div>

    {f'''
    <div class="card">
        <h3>{tr(request, "Deferral History", "سجل التأجيلات")}</h3>
        <table>
            <thead><tr>
                <th>{tr(request, "Original Month", "الشهر الأصلي")}</th>
                <th>{tr(request, "Deferred To", "مؤجل إلى")}</th>
                <th>{tr(request, "Amount", "المبلغ")}</th>
                <th>{tr(request, "Reason", "السبب")}</th>
            </tr></thead>
            <tbody>{deferral_rows}</tbody>
        </table>
    </div>
    ''' if deferrals else ""}
    """
    return HTMLResponse(render_page(tr(request, "Employee Advance", "سلفة الموظف"), html, lang, current_path=request.url.path))


@router.post(f"{BASE_ROUTE}/{{advance_id}}/defer-installment")
def advance_defer_installment(
    request: Request,
    advance_id: int,
    installment_id: int = Form(...),
    reason: str = Form(""),
):
    conn = get_conn()
    ok, msg_text = defer_installment(conn, advance_id, installment_id, safe(reason))
    if ok:
        conn.commit()
    conn.close()
    msg = tr(request, msg_text, msg_text)
    return RedirectResponse(with_lang(request, f"{BASE_ROUTE}/{advance_id}") + f"&msg={quote(msg)}", status_code=302)

