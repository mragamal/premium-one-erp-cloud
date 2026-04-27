from html import escape
from urllib.parse import quote

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse

from db import get_conn
from layout import render_page
from modules.accounting.employee_advances import (
    allocate_payroll_advance_deductions,
    ensure_advances_tables,
    get_employee_due_advance_total,
    get_employee_due_advances,
)
from modules.hr.attendance import ensure_attendance_tables
from modules.hr.employees import ensure_employees_table, safe, to_float

router = APIRouter()


def money(value):
    try:
        return f"{float(value or 0):,.2f}"
    except Exception:
        return "0.00"


def ensure_column(conn, table_name, column_name, alter_sql):
    cols = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    names = [c["name"] for c in cols]
    if column_name not in names:
        conn.execute(alter_sql)


def ensure_payroll_tables():
    ensure_employees_table()
    ensure_attendance_tables()
    ensure_advances_tables()
    conn = get_conn()

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS payroll_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payroll_no TEXT UNIQUE,
            payroll_month INTEGER,
            payroll_year INTEGER,
            period_from TEXT,
            period_to TEXT,
            payment_date TEXT,
            working_days_basis REAL DEFAULT 26,
            notes TEXT,
            status TEXT DEFAULT 'draft',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS payroll_lines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payroll_run_id INTEGER NOT NULL,
            employee_id INTEGER NOT NULL,
            employee_code TEXT,
            employee_name TEXT,
            department TEXT,
            job_title TEXT,
            basic_salary REAL DEFAULT 0,
            housing_allowance REAL DEFAULT 0,
            transport_allowance REAL DEFAULT 0,
            other_allowance REAL DEFAULT 0,
            attendance_days REAL DEFAULT 0,
            absent_days REAL DEFAULT 0,
            worked_hours REAL DEFAULT 0,
            overtime_hours REAL DEFAULT 0,
            overtime_amount REAL DEFAULT 0,
            bonus_amount REAL DEFAULT 0,
            deduction_amount REAL DEFAULT 0,
            advance_deduction REAL DEFAULT 0,
            absence_deduction REAL DEFAULT 0,
            insurance_employee_amount REAL DEFAULT 0,
            insurance_employer_amount REAL DEFAULT 0,
            gross_amount REAL DEFAULT 0,
            net_amount REAL DEFAULT 0,
            remarks TEXT
        )
        """
    )

    ensure_column(conn, "payroll_runs", "payroll_no", "ALTER TABLE payroll_runs ADD COLUMN payroll_no TEXT")
    ensure_column(conn, "payroll_runs", "payroll_month", "ALTER TABLE payroll_runs ADD COLUMN payroll_month INTEGER")
    ensure_column(conn, "payroll_runs", "payroll_year", "ALTER TABLE payroll_runs ADD COLUMN payroll_year INTEGER")
    ensure_column(conn, "payroll_runs", "period_from", "ALTER TABLE payroll_runs ADD COLUMN period_from TEXT")
    ensure_column(conn, "payroll_runs", "period_to", "ALTER TABLE payroll_runs ADD COLUMN period_to TEXT")
    ensure_column(conn, "payroll_runs", "payment_date", "ALTER TABLE payroll_runs ADD COLUMN payment_date TEXT")
    ensure_column(conn, "payroll_runs", "working_days_basis", "ALTER TABLE payroll_runs ADD COLUMN working_days_basis REAL DEFAULT 26")
    ensure_column(conn, "payroll_runs", "notes", "ALTER TABLE payroll_runs ADD COLUMN notes TEXT")
    ensure_column(conn, "payroll_runs", "status", "ALTER TABLE payroll_runs ADD COLUMN status TEXT DEFAULT 'draft'")
    ensure_column(conn, "payroll_runs", "created_at", "ALTER TABLE payroll_runs ADD COLUMN created_at TEXT DEFAULT CURRENT_TIMESTAMP")

    ensure_column(conn, "payroll_lines", "employee_code", "ALTER TABLE payroll_lines ADD COLUMN employee_code TEXT")
    ensure_column(conn, "payroll_lines", "employee_name", "ALTER TABLE payroll_lines ADD COLUMN employee_name TEXT")
    ensure_column(conn, "payroll_lines", "department", "ALTER TABLE payroll_lines ADD COLUMN department TEXT")
    ensure_column(conn, "payroll_lines", "job_title", "ALTER TABLE payroll_lines ADD COLUMN job_title TEXT")
    ensure_column(conn, "payroll_lines", "basic_salary", "ALTER TABLE payroll_lines ADD COLUMN basic_salary REAL DEFAULT 0")
    ensure_column(conn, "payroll_lines", "housing_allowance", "ALTER TABLE payroll_lines ADD COLUMN housing_allowance REAL DEFAULT 0")
    ensure_column(conn, "payroll_lines", "transport_allowance", "ALTER TABLE payroll_lines ADD COLUMN transport_allowance REAL DEFAULT 0")
    ensure_column(conn, "payroll_lines", "other_allowance", "ALTER TABLE payroll_lines ADD COLUMN other_allowance REAL DEFAULT 0")
    ensure_column(conn, "payroll_lines", "attendance_days", "ALTER TABLE payroll_lines ADD COLUMN attendance_days REAL DEFAULT 0")
    ensure_column(conn, "payroll_lines", "absent_days", "ALTER TABLE payroll_lines ADD COLUMN absent_days REAL DEFAULT 0")
    ensure_column(conn, "payroll_lines", "worked_hours", "ALTER TABLE payroll_lines ADD COLUMN worked_hours REAL DEFAULT 0")
    ensure_column(conn, "payroll_lines", "overtime_hours", "ALTER TABLE payroll_lines ADD COLUMN overtime_hours REAL DEFAULT 0")
    ensure_column(conn, "payroll_lines", "overtime_amount", "ALTER TABLE payroll_lines ADD COLUMN overtime_amount REAL DEFAULT 0")
    ensure_column(conn, "payroll_lines", "bonus_amount", "ALTER TABLE payroll_lines ADD COLUMN bonus_amount REAL DEFAULT 0")
    ensure_column(conn, "payroll_lines", "deduction_amount", "ALTER TABLE payroll_lines ADD COLUMN deduction_amount REAL DEFAULT 0")
    ensure_column(conn, "payroll_lines", "advance_deduction", "ALTER TABLE payroll_lines ADD COLUMN advance_deduction REAL DEFAULT 0")
    ensure_column(conn, "payroll_lines", "absence_deduction", "ALTER TABLE payroll_lines ADD COLUMN absence_deduction REAL DEFAULT 0")
    ensure_column(conn, "payroll_lines", "insurance_employee_amount", "ALTER TABLE payroll_lines ADD COLUMN insurance_employee_amount REAL DEFAULT 0")
    ensure_column(conn, "payroll_lines", "insurance_employer_amount", "ALTER TABLE payroll_lines ADD COLUMN insurance_employer_amount REAL DEFAULT 0")
    ensure_column(conn, "payroll_lines", "gross_amount", "ALTER TABLE payroll_lines ADD COLUMN gross_amount REAL DEFAULT 0")
    ensure_column(conn, "payroll_lines", "net_amount", "ALTER TABLE payroll_lines ADD COLUMN net_amount REAL DEFAULT 0")
    ensure_column(conn, "payroll_lines", "remarks", "ALTER TABLE payroll_lines ADD COLUMN remarks TEXT")

    conn.commit()
    conn.close()


def next_payroll_no():
    conn = get_conn()
    row = conn.execute(
        """
        SELECT payroll_no
        FROM payroll_runs
        WHERE COALESCE(payroll_no, '') <> ''
        ORDER BY id DESC
        LIMIT 1
        """
    ).fetchone()
    conn.close()
    last = safe(row["payroll_no"]) if row else ""
    if not last:
        return "PAY-0001"
    try:
        num = int(last.split("-")[-1])
    except Exception:
        num = 0
    return f"PAY-{num + 1:04d}"


def recalc_payroll_totals(conn, run_id):
    rows = conn.execute(
        """
        SELECT *
        FROM payroll_lines
        WHERE payroll_run_id = ?
        ORDER BY id
        """,
        (run_id,),
    ).fetchall()

    for row in rows:
        gross = (
            float(row["basic_salary"] or 0)
            + float(row["housing_allowance"] or 0)
            + float(row["transport_allowance"] or 0)
            + float(row["other_allowance"] or 0)
            + float(row["overtime_amount"] or 0)
            + float(row["bonus_amount"] or 0)
        )
        total_deductions = (
            float(row["deduction_amount"] or 0)
            + float(row["advance_deduction"] or 0)
            + float(row["absence_deduction"] or 0)
            + float(row["insurance_employee_amount"] or 0)
        )
        net = gross - total_deductions
        conn.execute(
            """
            UPDATE payroll_lines
            SET gross_amount = ?, net_amount = ?
            WHERE id = ?
            """,
            (gross, net, row["id"]),
        )


def attendance_summary_map(conn, period_from, period_to):
    rows = conn.execute(
        """
        SELECT
            employee_id,
            COUNT(DISTINCT attendance_date) AS attendance_days,
            COALESCE(SUM(worked_hours), 0) AS worked_hours,
            COALESCE(SUM(overtime_hours), 0) AS overtime_hours
        FROM attendance_logs
        WHERE attendance_date >= ?
          AND attendance_date <= ?
          AND LOWER(COALESCE(status, 'present')) IN (
              'present',
              'worked',
              'onsite',
              'late',
              'early_leave',
              'late_and_early_leave'
          )
        GROUP BY employee_id
        """,
        (safe(period_from), safe(period_to)),
    ).fetchall()
    return {
        int(row["employee_id"]): {
            "attendance_days": float(row["attendance_days"] or 0),
            "worked_hours": float(row["worked_hours"] or 0),
            "overtime_hours": float(row["overtime_hours"] or 0),
        }
        for row in rows
        if row["employee_id"] is not None
    }


def _advance_deduction_note(conn, employee_id: int, payroll_month: int, payroll_year: int, advance_deduction: float):
    due_advances = get_employee_due_advances(conn, employee_id, payroll_month, payroll_year)
    if advance_deduction > 0 and due_advances:
        labels = ", ".join(
            f"{safe(item.get('advance_no'))}:{money(item.get('due_amount', 0))}"
            for item in due_advances[:3]
        )
        if len(due_advances) > 3:
            labels += ", ..."
        return f"Advance deducted ({money(advance_deduction)}). Due: {labels}"

    active_advances = conn.execute(
        """
        SELECT advance_no, start_month, start_year
        FROM employee_advances
        WHERE employee_id = ?
          AND LOWER(COALESCE(status, 'active')) IN ('active', 'open')
        ORDER BY start_year, start_month, id
        """,
        (employee_id,),
    ).fetchall()
    if not active_advances:
        return "No active advances."

    current_period_key = int(payroll_year or 0) * 100 + int(payroll_month or 0)
    future_only = True
    nearest_no = ""
    nearest_month = 0
    nearest_year = 0
    nearest_key = 999999
    for row in active_advances:
        sm = int(row["start_month"] or 0)
        sy = int(row["start_year"] or 0)
        if sm <= 0 or sy <= 0:
            future_only = False
            continue
        k = sy * 100 + sm
        if k <= current_period_key:
            future_only = False
        if k < nearest_key:
            nearest_key = k
            nearest_no = safe(row["advance_no"])
            nearest_month = sm
            nearest_year = sy

    if future_only and nearest_no:
        return f"No deduction: advance starts at {nearest_month:02d}/{nearest_year} ({nearest_no})."
    return "No due installment for this payroll period."


ensure_payroll_tables()


@router.get("/ui/hr/payroll", response_class=HTMLResponse)
def payroll_list(request: Request):
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT pr.*,
               COUNT(pl.id) AS employee_count,
               COALESCE(SUM(pl.net_amount), 0) AS total_net
        FROM payroll_runs pr
        LEFT JOIN payroll_lines pl ON pl.payroll_run_id = pr.id
        GROUP BY pr.id
        ORDER BY pr.id DESC
        """
    ).fetchall()
    conn.close()

    msg = safe(request.query_params.get("msg"))
    msg_html = f'<div class="msg success">{escape(msg)}</div>' if msg else ""

    body = ""
    for row in rows:
        status_cls = "green" if safe(row["status"]).lower() == "posted" else "orange"
        delete_btn = ""
        if safe(row["status"]).lower() == "draft":
            delete_btn = (
                f'<form method="post" action="/ui/hr/payroll/{row["id"]}/delete" style="display:inline;" '
                f'onsubmit="return confirm(\'Delete this payroll draft?\');">'
                f'<button class="btn red" type="submit">Delete</button></form>'
            )
        body += f"""
        <tr>
            <td><a class="btn gray" href="/ui/hr/payroll/{row['id']}">{escape(safe(row['payroll_no']))}</a></td>
            <td>{int(row['payroll_month'] or 0):02d}/{row['payroll_year'] or ''}</td>
            <td>{escape(safe(row['period_from']))}</td>
            <td>{escape(safe(row['period_to']))}</td>
            <td>{escape(safe(row['payment_date']))}</td>
            <td>{int(row['employee_count'] or 0)}</td>
            <td class="number-cell">{money(row['total_net'])}</td>
            <td><span class="status-chip {status_cls}">{escape(safe(row['status']) or 'draft')}</span></td>
            <td>
                <a class="btn blue" href="/ui/hr/payroll/{row['id']}">Open</a>
                {delete_btn}
            </td>
        </tr>
        """

    if not body:
        body = "<tr><td colspan='9' style='text-align:center;'>No payroll runs found.</td></tr>"

    html = f"""
    <div class="card">
        {msg_html}
        <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;">
            <h2>Payroll</h2>
            <a class="btn green" href="/ui/hr/payroll/new">+ New Payroll Run</a>
        </div>
    </div>

    <div class="card">
        <table>
            <tr>
                <th>Payroll No</th>
                <th>Month</th>
                <th>Period From</th>
                <th>Period To</th>
                <th>Payment Date</th>
                <th>Employees</th>
                <th>Total Net</th>
                <th>Status</th>
                <th>Action</th>
            </tr>
            {body}
        </table>
    </div>
    """
    return HTMLResponse(render_page("Payroll", html, "en", current_path=request.url.path))


@router.get("/ui/hr/payroll/new", response_class=HTMLResponse)
def payroll_new(request: Request):
    html = f"""
    <div class="card">
        <h2>New Payroll Run</h2>
        <form method="post" action="/ui/hr/payroll/new">
            <div class="row">
                <div class="col">
                    <label>Payroll No</label>
                    <input name="payroll_no" value="{next_payroll_no()}" readonly>
                </div>
                <div class="col">
                    <label>Payroll Month</label>
                    <input type="number" min="1" max="12" name="payroll_month" required>
                </div>
            </div>

            <div class="row" style="margin-top:14px;">
                <div class="col">
                    <label>Payroll Year</label>
                    <input type="number" min="2020" max="2100" name="payroll_year" required>
                </div>
                <div class="col">
                    <label>Payment Date</label>
                    <input type="date" name="payment_date" required>
                </div>
            </div>

            <div class="row" style="margin-top:14px;">
                <div class="col">
                    <label>Period From</label>
                    <input type="date" name="period_from" required>
                </div>
                <div class="col">
                    <label>Period To</label>
                    <input type="date" name="period_to" required>
                </div>
            </div>

            <div class="row" style="margin-top:14px;">
                <div class="col">
                    <label>Working Days Basis</label>
                    <input type="number" step="0.01" name="working_days_basis" value="26" required>
                </div>
                <div class="col">
                    <label>Notes</label>
                    <input name="notes">
                </div>
            </div>

            <div class="card" style="margin-top:18px;">
                <h3>Payroll Engine</h3>
                <p class="section-note">This payroll run will calculate attendance days, absence deduction, overtime, and employee insurance deduction based on imported attendance / biometric logs for the selected period.</p>
            </div>

            <div style="margin-top:20px;">
                <button class="btn green" type="submit">Generate Payroll Draft</button>
                <a class="btn gray" href="/ui/hr/payroll">Back</a>
            </div>
        </form>
    </div>
    """
    return HTMLResponse(render_page("New Payroll", html, "en", current_path=request.url.path))


@router.post("/ui/hr/payroll/new")
def payroll_create(
    payroll_no: str = Form(""),
    payroll_month: int = Form(...),
    payroll_year: int = Form(...),
    period_from: str = Form(""),
    period_to: str = Form(""),
    payment_date: str = Form(""),
    working_days_basis: str = Form("26"),
    notes: str = Form(""),
):
    conn = get_conn()
    attendance_map = attendance_summary_map(conn, period_from, period_to)
    employees = conn.execute(
        """
        SELECT *
        FROM employees
        WHERE COALESCE(is_active, 1) = 1
        ORDER BY code, name
        """
    ).fetchall()

    if not employees:
        conn.close()
        return RedirectResponse("/ui/hr/payroll?msg=" + quote("No active employees found to generate payroll."), status_code=302)

    run_cur = conn.execute(
        """
        INSERT INTO payroll_runs (
            payroll_no, payroll_month, payroll_year, period_from, period_to, payment_date, notes, status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, 'draft')
        """,
        (
            safe(payroll_no) or next_payroll_no(),
            int(payroll_month or 0),
            int(payroll_year or 0),
            safe(period_from),
            safe(period_to),
            safe(payment_date),
            safe(notes),
        ),
    )
    run_id = run_cur.lastrowid
    basis_days = max(to_float(working_days_basis, 26), 1)
    conn.execute("UPDATE payroll_runs SET working_days_basis = ? WHERE id = ?", (basis_days, run_id))

    for emp in employees:
        att = attendance_map.get(int(emp["id"]), {})
        attendance_days = min(float(att.get("attendance_days", 0)), basis_days)
        absent_days = max(basis_days - attendance_days, 0)
        worked_hours = float(att.get("worked_hours", 0))
        overtime_hours = float(att.get("overtime_hours", 0))

        fixed_comp = (
            float(emp["basic_salary"] or 0)
            + float(emp["housing_allowance"] or 0)
            + float(emp["transport_allowance"] or 0)
            + float(emp["other_allowance"] or 0)
        )
        daily_rate = fixed_comp / basis_days if basis_days > 0 else 0
        expected_daily_hours = max(float(emp["expected_daily_hours"] or 8), 1)
        hourly_rate = (float(emp["basic_salary"] or 0) / basis_days / expected_daily_hours) if basis_days > 0 else 0
        overtime_amount = overtime_hours * hourly_rate
        absence_deduction = absent_days * daily_rate
        insurance_salary = float(emp["insurance_salary"] or 0) or float(emp["basic_salary"] or 0)
        insurance_employee_amount = 0.0
        insurance_employer_amount = 0.0
        if int(emp["insurance_applicable"] or 0) == 1:
            insurance_employee_amount = insurance_salary * (float(emp["insurance_employee_rate"] or 0) / 100.0)
            insurance_employer_amount = insurance_salary * (float(emp["insurance_employer_rate"] or 0) / 100.0)
        advance_deduction = get_employee_due_advance_total(conn, emp["id"], payroll_month, payroll_year)
        remarks = _advance_deduction_note(
            conn,
            int(emp["id"]),
            int(payroll_month or 0),
            int(payroll_year or 0),
            float(advance_deduction or 0),
        )

        conn.execute(
            """
            INSERT INTO payroll_lines (
                payroll_run_id, employee_id, employee_code, employee_name, department, job_title,
                basic_salary, housing_allowance, transport_allowance, other_allowance,
                attendance_days, absent_days, worked_hours, overtime_hours,
                overtime_amount, bonus_amount, deduction_amount, advance_deduction, absence_deduction,
                insurance_employee_amount, insurance_employer_amount,
                gross_amount, net_amount, remarks
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                emp["id"],
                safe(emp["code"]),
                safe(emp["name"]),
                safe(emp["department"]),
                safe(emp["job_title"]),
                float(emp["basic_salary"] or 0),
                float(emp["housing_allowance"] or 0),
                float(emp["transport_allowance"] or 0),
                float(emp["other_allowance"] or 0),
                attendance_days,
                absent_days,
                worked_hours,
                overtime_hours,
                overtime_amount,
                0,
                0,
                advance_deduction,
                absence_deduction,
                insurance_employee_amount,
                insurance_employer_amount,
                0,
                0,
                remarks,
            ),
        )

    recalc_payroll_totals(conn, run_id)
    conn.commit()
    conn.close()
    return RedirectResponse(f"/ui/hr/payroll/{run_id}", status_code=302)


@router.get("/ui/hr/payroll/{run_id}", response_class=HTMLResponse)
def payroll_open(request: Request, run_id: int):
    conn = get_conn()
    run = conn.execute("SELECT * FROM payroll_runs WHERE id = ? LIMIT 1", (run_id,)).fetchone()
    if not run:
        conn.close()
        return HTMLResponse("Payroll run not found", status_code=404)

    lines = conn.execute(
        """
        SELECT *
        FROM payroll_lines
        WHERE payroll_run_id = ?
        ORDER BY employee_code, employee_name, id
        """,
        (run_id,),
    ).fetchall()

    total_gross = 0.0
    total_net = 0.0
    total_ded = 0.0
    total_employer_insurance = 0.0
    body = ""
    for line in lines:
        gross = float(line["gross_amount"] or 0)
        net = float(line["net_amount"] or 0)
        ded = (
            float(line["deduction_amount"] or 0)
            + float(line["advance_deduction"] or 0)
            + float(line["absence_deduction"] or 0)
            + float(line["insurance_employee_amount"] or 0)
        )
        total_gross += gross
        total_net += net
        total_ded += ded
        total_employer_insurance += float(line["insurance_employer_amount"] or 0)
        earnings_breakdown = (
            f"Basic: {money(line['basic_salary'])} | "
            f"Housing: {money(line['housing_allowance'])} | "
            f"Transport: {money(line['transport_allowance'])} | "
            f"Other: {money(line['other_allowance'])} | "
            f"OT: {money(line['overtime_amount'])} | "
            f"Bonus: {money(line['bonus_amount'])}"
        )
        deductions_breakdown = (
            f"Manual: {money(line['deduction_amount'])} | "
            f"Advance: {money(line['advance_deduction'])} | "
            f"Absence: {money(line['absence_deduction'])} | "
            f"Emp. Insurance: {money(line['insurance_employee_amount'])}"
        )
        body += f"""
        <tr>
            <td>{escape(safe(line['employee_code']))}</td>
            <td>{escape(safe(line['employee_name']))}</td>
            <td class="number-cell">{float(line['attendance_days'] or 0):,.2f}</td>
            <td class="number-cell">{float(line['absent_days'] or 0):,.2f}</td>
            <td class="number-cell">{float(line['overtime_hours'] or 0):,.2f}</td>
            <td>{escape(safe(line['department']))}</td>
            <td>{escape(safe(line['job_title']))}</td>
            <td class="number-cell">{money(gross)}</td>
            <td class="number-cell">{money(ded)}</td>
            <td class="number-cell">{money(net)}</td>
            <td>
                <details>
                    <summary style="cursor:pointer; color:#1b57d0; font-weight:700;">View</summary>
                    <div style="margin-top:6px; font-size:12px; color:#4b5f7a; line-height:1.6;">
                        <div><b>Earnings:</b> {earnings_breakdown}</div>
                        <div><b>Deductions:</b> {deductions_breakdown}</div>
                    </div>
                </details>
            </td>
            <td>{escape(safe(line['remarks']))}</td>
        </tr>
        """

    if not body:
        body = "<tr><td colspan='12' style='text-align:center;'>No payroll lines found.</td></tr>"

    action_buttons = f'<a class="btn blue" href="/ui/hr/payroll/{run_id}/edit">Edit Draft</a>' if safe(run["status"]).lower() == "draft" else ""
    post_button = ""
    delete_button = ""
    if safe(run["status"]).lower() == "draft":
        post_button = f"""
        <form method="post" action="/ui/hr/payroll/{run_id}/post" style="display:inline;">
            <button class="btn green" type="submit">Post Payroll</button>
        </form>
        """
        delete_button = f"""
        <form method="post" action="/ui/hr/payroll/{run_id}/delete" style="display:inline;" onsubmit="return confirm('Delete this payroll draft?');">
            <button class="btn red" type="submit">Delete Draft</button>
        </form>
        """

    status_cls = "green" if safe(run["status"]).lower() == "posted" else "orange"
    html = f"""
    <div class="card">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap;">
            <div>
                <h2>Payroll {escape(safe(run['payroll_no']))}</h2>
                <p><b>Month:</b> {int(run['payroll_month'] or 0):02d}/{run['payroll_year'] or ''}</p>
                <p><b>Period:</b> {escape(safe(run['period_from']))} to {escape(safe(run['period_to']))}</p>
                <p><b>Payment Date:</b> {escape(safe(run['payment_date']))}</p>
                <p><b>Working Days Basis:</b> {float(run['working_days_basis'] or 0):,.2f}</p>
                <p><b>Status:</b> <span class="status-chip {status_cls}">{escape(safe(run['status']))}</span></p>
                <p><b>Notes:</b> {escape(safe(run['notes']))}</p>
            </div>
            <div class="kpi-grid" style="min-width:280px;">
                <div class="kpi-card">
                    <div class="kpi-label">Employees</div>
                    <div class="kpi-value">{len(lines)}</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">Gross</div>
                    <div class="kpi-value">{money(total_gross)}</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">Deductions</div>
                    <div class="kpi-value">{money(total_ded)}</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">Net</div>
                    <div class="kpi-value">{money(total_net)}</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">Employer Insurance</div>
                    <div class="kpi-value">{money(total_employer_insurance)}</div>
                </div>
            </div>
        </div>

        <div style="margin-top:16px;display:flex;gap:8px;flex-wrap:wrap;">
            <a class="btn gray" href="/ui/hr/payroll">Back</a>
            {action_buttons}
            {post_button}
            {delete_button}
        </div>
    </div>

    <div class="card">
        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>Code</th>
                        <th>Name</th>
                        <th>Attendance</th>
                        <th>Absent</th>
                        <th>OT Hours</th>
                        <th>Department</th>
                        <th>Job Title</th>
                        <th>Gross</th>
                        <th>Deductions</th>
                        <th>Net</th>
                        <th>Breakdown</th>
                        <th>Advance Note</th>
                    </tr>
                </thead>
                <tbody>
                    {body}
                </tbody>
            </table>
        </div>
    </div>
    """
    conn.close()
    return HTMLResponse(render_page("Payroll", html, "en", current_path=request.url.path))


@router.get("/ui/hr/payroll/{run_id}/edit", response_class=HTMLResponse)
def payroll_edit(request: Request, run_id: int):
    conn = get_conn()
    run = conn.execute("SELECT * FROM payroll_runs WHERE id = ? LIMIT 1", (run_id,)).fetchone()
    if not run:
        conn.close()
        return HTMLResponse("Payroll run not found", status_code=404)
    if safe(run["status"]).lower() != "draft":
        conn.close()
        return RedirectResponse("/ui/hr/payroll?msg=" + quote("Only draft payroll can be edited."), status_code=302)

    lines = conn.execute(
        """
        SELECT *
        FROM payroll_lines
        WHERE payroll_run_id = ?
        ORDER BY employee_code, employee_name, id
        """,
        (run_id,),
    ).fetchall()
    conn.close()

    rows_html = ""
    for line in lines:
        rows_html += f"""
        <tr>
            <td>{escape(safe(line['employee_code']))}<input type="hidden" name="line_id_{line['id']}" value="{line['id']}"></td>
            <td>{escape(safe(line['employee_name']))}</td>
            <td class="number-cell">{float(line['attendance_days'] or 0):,.2f}</td>
            <td class="number-cell">{float(line['absent_days'] or 0):,.2f}</td>
            <td class="number-cell">{float(line['overtime_hours'] or 0):,.2f}</td>
            <td class="number-cell">{money(line['basic_salary'])}</td>
            <td class="number-cell">{money(line['housing_allowance'])}</td>
            <td class="number-cell">{money(line['transport_allowance'])}</td>
            <td class="number-cell">{money(line['other_allowance'])}</td>
            <td><input class="line-input line-overtime" type="number" step="0.01" name="overtime_amount_{line['id']}" value="{safe(line['overtime_amount'] or '0')}"></td>
            <td><input class="line-input line-bonus" type="number" step="0.01" name="bonus_amount_{line['id']}" value="{safe(line['bonus_amount'] or '0')}"></td>
            <td><input class="line-input line-deduction" type="number" step="0.01" name="deduction_amount_{line['id']}" value="{safe(line['deduction_amount'] or '0')}"></td>
            <td><input class="line-input line-advance" type="number" step="0.01" name="advance_deduction_{line['id']}" value="{safe(line['advance_deduction'] or '0')}"></td>
            <td><input class="line-input line-absence" type="number" step="0.01" name="absence_deduction_{line['id']}" value="{safe(line['absence_deduction'] or '0')}"></td>
            <td class="number-cell">{money(line['insurance_employee_amount'])}</td>
            <td class="number-cell">{money(line['insurance_employer_amount'])}</td>
            <td><input name="remarks_{line['id']}" value="{escape(safe(line['remarks']))}"></td>
            <td class="number-cell line-gross">{money(line['gross_amount'])}</td>
            <td class="number-cell line-net">{money(line['net_amount'])}</td>
        </tr>
        """

    html = f"""
    <div class="card">
        <h2>Edit Payroll Draft {escape(safe(run['payroll_no']))}</h2>
        <p class="section-note">Attendance days, absent days, overtime hours, and insurance are calculated automatically from employee setup and biometric attendance. You can still adjust overtime amount, bonuses, and manual deductions before posting.</p>
    </div>

    <div class="card">
        <form method="post" action="/ui/hr/payroll/{run_id}/edit">
            <div class="table-wrap">
                <table id="payrollEditTable">
                    <tr>
                        <th>Code</th>
                        <th>Name</th>
                        <th>Attendance</th>
                        <th>Absent</th>
                        <th>OT Hours</th>
                        <th>Basic</th>
                        <th>Housing</th>
                        <th>Transport</th>
                        <th>Other</th>
                        <th>Overtime</th>
                        <th>Bonus</th>
                        <th>Deduction</th>
                        <th>Advance</th>
                        <th>Absence</th>
                        <th>Emp. Insurance</th>
                        <th>Comp. Insurance</th>
                        <th>Remarks</th>
                        <th>Gross</th>
                        <th>Net</th>
                    </tr>
                    {rows_html}
                </table>
            </div>

            <div style="margin-top:18px;">
                <button class="btn green" type="submit">Save Draft</button>
                <a class="btn gray" href="/ui/hr/payroll/{run_id}">Back</a>
            </div>
        </form>
    </div>

    <script>
    function toNum(value) {{
        const n = parseFloat(value || "0");
        return isNaN(n) ? 0 : n;
    }}

    function fmt(value) {{
        return value.toLocaleString(undefined, {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }});
    }}

    function recalcRow(row) {{
        const basic = toNum(row.children[5].innerText.replace(/,/g, ""));
        const housing = toNum(row.children[6].innerText.replace(/,/g, ""));
        const transport = toNum(row.children[7].innerText.replace(/,/g, ""));
        const other = toNum(row.children[8].innerText.replace(/,/g, ""));
        const overtime = toNum(row.querySelector(".line-overtime")?.value);
        const bonus = toNum(row.querySelector(".line-bonus")?.value);
        const deduction = toNum(row.querySelector(".line-deduction")?.value);
        const advance = toNum(row.querySelector(".line-advance")?.value);
        const absence = toNum(row.querySelector(".line-absence")?.value);
        const insurance = toNum(row.children[14].innerText.replace(/,/g, ""));
        const gross = basic + housing + transport + other + overtime + bonus;
        const net = gross - deduction - advance - absence - insurance;
        row.querySelector(".line-gross").innerText = fmt(gross);
        row.querySelector(".line-net").innerText = fmt(net);
    }}

    window.addEventListener("DOMContentLoaded", function() {{
        document.querySelectorAll("#payrollEditTable tr").forEach(function(row) {{
            row.querySelectorAll(".line-input").forEach(function(input) {{
                input.addEventListener("input", function() {{ recalcRow(row); }});
            }});
        }});
    }});
    </script>
    """
    return HTMLResponse(render_page("Edit Payroll", html, "en", current_path=request.url.path))


@router.post("/ui/hr/payroll/{run_id}/edit")
async def payroll_update(request: Request, run_id: int):
    form = await request.form()
    conn = get_conn()
    run = conn.execute("SELECT * FROM payroll_runs WHERE id = ? LIMIT 1", (run_id,)).fetchone()
    if not run:
        conn.close()
        return HTMLResponse("Payroll run not found", status_code=404)
    if safe(run["status"]).lower() != "draft":
        conn.close()
        return RedirectResponse("/ui/hr/payroll?msg=" + quote("Only draft payroll can be edited."), status_code=302)

    line_ids = conn.execute("SELECT id FROM payroll_lines WHERE payroll_run_id = ?", (run_id,)).fetchall()
    for row in line_ids:
        line_id = row["id"]
        conn.execute(
            """
            UPDATE payroll_lines
            SET overtime_amount = ?,
                bonus_amount = ?,
                deduction_amount = ?,
                advance_deduction = ?,
                absence_deduction = ?,
                remarks = ?
            WHERE id = ?
            """,
            (
                to_float(form.get(f"overtime_amount_{line_id}")),
                to_float(form.get(f"bonus_amount_{line_id}")),
                to_float(form.get(f"deduction_amount_{line_id}")),
                to_float(form.get(f"advance_deduction_{line_id}")),
                to_float(form.get(f"absence_deduction_{line_id}")),
                safe(form.get(f"remarks_{line_id}")),
                line_id,
            ),
        )

    recalc_payroll_totals(conn, run_id)
    conn.commit()
    conn.close()
    return RedirectResponse(f"/ui/hr/payroll/{run_id}", status_code=302)


@router.post("/ui/hr/payroll/{run_id}/post")
def payroll_post(run_id: int):
    conn = get_conn()
    run = conn.execute("SELECT * FROM payroll_runs WHERE id = ? LIMIT 1", (run_id,)).fetchone()
    if not run:
        conn.close()
        return HTMLResponse("Payroll run not found", status_code=404)
    if safe(run["status"]).lower() != "draft":
        conn.close()
        return RedirectResponse("/ui/hr/payroll?msg=" + quote("Only draft payroll can be posted."), status_code=302)
    allocate_payroll_advance_deductions(conn, run_id)
    conn.execute("UPDATE payroll_runs SET status = 'posted' WHERE id = ?", (run_id,))
    conn.commit()
    conn.close()
    return RedirectResponse(f"/ui/hr/payroll/{run_id}", status_code=302)


@router.post("/ui/hr/payroll/{run_id}/delete")
def payroll_delete(run_id: int):
    conn = get_conn()
    run = conn.execute("SELECT * FROM payroll_runs WHERE id = ? LIMIT 1", (run_id,)).fetchone()
    if not run:
        conn.close()
        return HTMLResponse("Payroll run not found", status_code=404)

    if safe(run["status"]).lower() != "draft":
        conn.close()
        return RedirectResponse("/ui/hr/payroll?msg=" + quote("Only draft payroll can be deleted."), status_code=302)

    conn.execute("DELETE FROM employee_advance_deductions WHERE payroll_run_id = ?", (run_id,))
    conn.execute("DELETE FROM payroll_lines WHERE payroll_run_id = ?", (run_id,))
    conn.execute("DELETE FROM payroll_runs WHERE id = ?", (run_id,))
    conn.commit()
    conn.close()
    return RedirectResponse("/ui/hr/payroll?msg=" + quote("Payroll draft deleted."), status_code=302)
