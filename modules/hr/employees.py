import csv
import io
from html import escape
from urllib.parse import quote

from fastapi import APIRouter, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse

from db import get_conn
from layout import render_page
from modules.hr.categories import category_options_html, ensure_categories_table

try:
    from openpyxl import Workbook, load_workbook
except Exception:
    Workbook = None
    load_workbook = None

router = APIRouter()


def safe(value):
    return "" if value is None else str(value).strip()


def money(value):
    try:
        return f"{float(value or 0):,.2f}"
    except Exception:
        return "0.00"


def to_float(value, default=0.0):
    try:
        return float(safe(value).replace(",", "") or default)
    except Exception:
        return float(default)


def to_int_flag(value, default=1):
    text = safe(value).lower()
    if text in ("1", "true", "yes", "y", "active"):
        return 1
    if text in ("0", "false", "no", "n", "inactive"):
        return 0
    try:
        return 1 if int(value) == 1 else 0
    except Exception:
        return int(default)


def resolve_category_id(conn, category_id="", category_code="", category_name=""):
    if safe(category_id).isdigit():
        return int(safe(category_id))

    code = safe(category_code)
    name = safe(category_name)
    if not code and not name:
        return None

    row = None
    if code:
        row = conn.execute(
            "SELECT id FROM employee_categories WHERE UPPER(COALESCE(code, '')) = UPPER(?) LIMIT 1",
            (code,),
        ).fetchone()
    if not row and name:
        row = conn.execute(
            "SELECT id FROM employee_categories WHERE UPPER(COALESCE(name, '')) = UPPER(?) LIMIT 1",
            (name,),
        ).fetchone()
    return int(row["id"]) if row else None


def ensure_column(conn, table_name, column_name, alter_sql):
    cols = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    names = [c["name"] for c in cols]
    if column_name not in names:
        conn.execute(alter_sql)


def ensure_employees_table():
    ensure_categories_table()
    conn = get_conn()

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT,
            category_id INTEGER,
            biometric_code TEXT,
            name TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            department TEXT,
            job_title TEXT,
            hire_date TEXT,
            national_id TEXT,
            payment_method TEXT DEFAULT 'bank_transfer',
            bank_name TEXT,
            bank_account TEXT,
            basic_salary REAL DEFAULT 0,
            housing_allowance REAL DEFAULT 0,
            transport_allowance REAL DEFAULT 0,
            other_allowance REAL DEFAULT 0,
            insurance_applicable INTEGER DEFAULT 1,
            insurance_number TEXT,
            insurance_salary REAL DEFAULT 0,
            insurance_employee_rate REAL DEFAULT 11,
            insurance_employer_rate REAL DEFAULT 18.75,
            expected_daily_hours REAL DEFAULT 8,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    ensure_column(conn, "employees", "code", "ALTER TABLE employees ADD COLUMN code TEXT")
    ensure_column(conn, "employees", "category_id", "ALTER TABLE employees ADD COLUMN category_id INTEGER")
    ensure_column(conn, "employees", "biometric_code", "ALTER TABLE employees ADD COLUMN biometric_code TEXT")
    ensure_column(conn, "employees", "phone", "ALTER TABLE employees ADD COLUMN phone TEXT")
    ensure_column(conn, "employees", "email", "ALTER TABLE employees ADD COLUMN email TEXT")
    ensure_column(conn, "employees", "department", "ALTER TABLE employees ADD COLUMN department TEXT")
    ensure_column(conn, "employees", "job_title", "ALTER TABLE employees ADD COLUMN job_title TEXT")
    ensure_column(conn, "employees", "hire_date", "ALTER TABLE employees ADD COLUMN hire_date TEXT")
    ensure_column(conn, "employees", "national_id", "ALTER TABLE employees ADD COLUMN national_id TEXT")
    ensure_column(conn, "employees", "payment_method", "ALTER TABLE employees ADD COLUMN payment_method TEXT DEFAULT 'bank_transfer'")
    ensure_column(conn, "employees", "bank_name", "ALTER TABLE employees ADD COLUMN bank_name TEXT")
    ensure_column(conn, "employees", "bank_account", "ALTER TABLE employees ADD COLUMN bank_account TEXT")
    ensure_column(conn, "employees", "basic_salary", "ALTER TABLE employees ADD COLUMN basic_salary REAL DEFAULT 0")
    ensure_column(conn, "employees", "housing_allowance", "ALTER TABLE employees ADD COLUMN housing_allowance REAL DEFAULT 0")
    ensure_column(conn, "employees", "transport_allowance", "ALTER TABLE employees ADD COLUMN transport_allowance REAL DEFAULT 0")
    ensure_column(conn, "employees", "other_allowance", "ALTER TABLE employees ADD COLUMN other_allowance REAL DEFAULT 0")
    ensure_column(conn, "employees", "insurance_applicable", "ALTER TABLE employees ADD COLUMN insurance_applicable INTEGER DEFAULT 1")
    ensure_column(conn, "employees", "insurance_number", "ALTER TABLE employees ADD COLUMN insurance_number TEXT")
    ensure_column(conn, "employees", "insurance_salary", "ALTER TABLE employees ADD COLUMN insurance_salary REAL DEFAULT 0")
    ensure_column(conn, "employees", "insurance_employee_rate", "ALTER TABLE employees ADD COLUMN insurance_employee_rate REAL DEFAULT 11")
    ensure_column(conn, "employees", "insurance_employer_rate", "ALTER TABLE employees ADD COLUMN insurance_employer_rate REAL DEFAULT 18.75")
    ensure_column(conn, "employees", "expected_daily_hours", "ALTER TABLE employees ADD COLUMN expected_daily_hours REAL DEFAULT 8")
    ensure_column(conn, "employees", "is_active", "ALTER TABLE employees ADD COLUMN is_active INTEGER DEFAULT 1")

    conn.commit()
    conn.close()


def next_employee_code():
    ensure_employees_table()
    conn = get_conn()
    row = conn.execute(
        """
        SELECT code
        FROM employees
        WHERE COALESCE(code, '') <> ''
        ORDER BY id DESC
        LIMIT 1
        """
    ).fetchone()
    conn.close()

    last = safe(row["code"]) if row else ""
    if not last:
        return "EMP-0001"
    try:
        num = int(last.split("-")[-1])
    except Exception:
        num = 0
    return f"EMP-{num + 1:04d}"


def employee_form_html(action, data=None):
    data = data or {}
    active_yes = "selected" if str(data.get("is_active", "1")) == "1" else ""
    active_no = "selected" if str(data.get("is_active", "1")) != "1" else ""

    payment_method = safe(data.get("payment_method") or "bank_transfer")
    selected_bank = "selected" if payment_method == "bank_transfer" else ""
    selected_cash = "selected" if payment_method == "cash" else ""
    insurance_yes = "selected" if str(data.get("insurance_applicable", "1")) == "1" else ""
    insurance_no = "selected" if str(data.get("insurance_applicable", "1")) != "1" else ""

    return f"""
    <div class="card">
        <h2>{'Edit Employee' if '/edit' in action else 'New Employee'}</h2>

        <form method="post" action="{action}">
            <div class="row">
                <div class="col">
                    <label>Code</label>
                    <input name="code" value="{escape(safe(data.get('code') or next_employee_code()))}" readonly>
                </div>
                <div class="col">
                    <label>Employee Name</label>
                    <input name="name" value="{escape(safe(data.get('name')))}" required>
                </div>
            </div>

            <div class="row" style="margin-top:14px;">
                <div class="col">
                    <label>Phone</label>
                    <input name="phone" value="{escape(safe(data.get('phone')))}">
                </div>
                <div class="col">
                    <label>Email</label>
                    <input name="email" value="{escape(safe(data.get('email')))}">
                </div>
            </div>

            <div class="row" style="margin-top:14px;">
                <div class="col">
                    <label>Biometric Code</label>
                    <input name="biometric_code" value="{escape(safe(data.get('biometric_code')))}">
                </div>
                <div class="col">
                    <label>Employee Category</label>
                    <select name="category_id">
                        {category_options_html(data.get('category_id') or '')}
                    </select>
                </div>
            </div>

            <div class="row" style="margin-top:14px;">
                <div class="col">
                    <label>Department</label>
                    <input name="department" value="{escape(safe(data.get('department')))}">
                </div>
                <div class="col">
                    <label>Job Title</label>
                    <input name="job_title" value="{escape(safe(data.get('job_title')))}">
                </div>
            </div>

            <div class="row" style="margin-top:14px;">
                <div class="col">
                    <label>Hire Date</label>
                    <input type="date" name="hire_date" value="{escape(safe(data.get('hire_date')))}">
                </div>
                <div class="col">
                    <label>National ID</label>
                    <input name="national_id" value="{escape(safe(data.get('national_id')))}">
                </div>
            </div>

            <div class="card" style="margin-top:18px;">
                <h3>Payroll Setup</h3>
                <div class="row">
                    <div class="col">
                        <label>Basic Salary</label>
                        <input type="number" step="0.01" name="basic_salary" value="{safe(data.get('basic_salary') or '0')}">
                    </div>
                    <div class="col">
                        <label>Housing Allowance</label>
                        <input type="number" step="0.01" name="housing_allowance" value="{safe(data.get('housing_allowance') or '0')}">
                    </div>
                </div>

                <div class="row" style="margin-top:14px;">
                    <div class="col">
                        <label>Expected Daily Hours</label>
                        <input type="number" step="0.01" name="expected_daily_hours" value="{safe(data.get('expected_daily_hours') or '8')}">
                    </div>
                    <div class="col">
                        <label>Transport Allowance</label>
                        <input type="number" step="0.01" name="transport_allowance" value="{safe(data.get('transport_allowance') or '0')}">
                    </div>
                </div>

                <div class="row" style="margin-top:14px;">
                    <div class="col">
                        <label>Other Allowance</label>
                        <input type="number" step="0.01" name="other_allowance" value="{safe(data.get('other_allowance') or '0')}">
                    </div>
                    <div class="col"></div>
                </div>

                <div class="row" style="margin-top:14px;">
                    <div class="col">
                        <label>Insurance Applicable</label>
                        <select name="insurance_applicable">
                            <option value="1" {insurance_yes}>Yes</option>
                            <option value="0" {insurance_no}>No</option>
                        </select>
                    </div>
                    <div class="col">
                        <label>Insurance Number</label>
                        <input name="insurance_number" value="{escape(safe(data.get('insurance_number')))}">
                    </div>
                </div>

                <div class="row" style="margin-top:14px;">
                    <div class="col">
                        <label>Insurance Salary</label>
                        <input type="number" step="0.01" name="insurance_salary" value="{safe(data.get('insurance_salary') or '0')}">
                    </div>
                    <div class="col">
                        <label>Employee Insurance Rate %</label>
                        <input type="number" step="0.01" name="insurance_employee_rate" value="{safe(data.get('insurance_employee_rate') or '11')}">
                    </div>
                </div>

                <div class="row" style="margin-top:14px;">
                    <div class="col">
                        <label>Employer Insurance Rate %</label>
                        <input type="number" step="0.01" name="insurance_employer_rate" value="{safe(data.get('insurance_employer_rate') or '18.75')}">
                    </div>
                    <div class="col"></div>
                </div>

                <div class="row" style="margin-top:14px;">
                    <div class="col">
                        <label>Payment Method</label>
                        <select name="payment_method">
                            <option value="bank_transfer" {selected_bank}>Bank Transfer</option>
                            <option value="cash" {selected_cash}>Cash</option>
                        </select>
                    </div>
                    <div class="col">
                        <label>Bank Name</label>
                        <input name="bank_name" value="{escape(safe(data.get('bank_name')))}">
                    </div>
                </div>

                <div class="row" style="margin-top:14px;">
                    <div class="col">
                        <label>Bank Account</label>
                        <input name="bank_account" value="{escape(safe(data.get('bank_account')))}">
                    </div>
                    <div class="col">
                        <label>Status</label>
                        <select name="is_active">
                            <option value="1" {active_yes}>Active</option>
                            <option value="0" {active_no}>Inactive</option>
                        </select>
                    </div>
                </div>
            </div>

            <div style="margin-top:20px;">
                <button class="btn green" type="submit">Save</button>
                <a class="btn gray" href="/ui/hr/employees">Back</a>
            </div>
        </form>
    </div>
    """


def get_header_value(row, aliases):
    for key in aliases:
        if key in row and safe(row.get(key)):
            return safe(row.get(key))
    return ""


def normalize_import_row(row):
    return {
        "code": get_header_value(row, ["code", "employee_code", "emp_code"]),
        "category_id": get_header_value(row, ["category_id"]),
        "category_code": get_header_value(row, ["category_code", "employee_category_code"]),
        "category_name": get_header_value(row, ["category_name", "employee_category"]),
        "biometric_code": get_header_value(row, ["biometric_code", "machine_code", "attendance_code"]),
        "name": get_header_value(row, ["name", "employee_name", "full_name"]),
        "phone": get_header_value(row, ["phone", "mobile"]),
        "email": get_header_value(row, ["email", "mail"]),
        "department": get_header_value(row, ["department", "dept"]),
        "job_title": get_header_value(row, ["job_title", "title", "position"]),
        "hire_date": get_header_value(row, ["hire_date", "joining_date", "join_date"]),
        "national_id": get_header_value(row, ["national_id", "id_no", "id_number"]),
        "payment_method": get_header_value(row, ["payment_method", "salary_method"]) or "bank_transfer",
        "bank_name": get_header_value(row, ["bank_name", "bank"]),
        "bank_account": get_header_value(row, ["bank_account", "account_no", "account_number"]),
        "basic_salary": get_header_value(row, ["basic_salary", "salary_basic", "basic"]) or "0",
        "housing_allowance": get_header_value(row, ["housing_allowance", "housing"]) or "0",
        "transport_allowance": get_header_value(row, ["transport_allowance", "transport"]) or "0",
        "other_allowance": get_header_value(row, ["other_allowance", "other"]) or "0",
        "insurance_applicable": get_header_value(row, ["insurance_applicable", "insured"]) or "1",
        "insurance_number": get_header_value(row, ["insurance_number", "social_insurance_no"]),
        "insurance_salary": get_header_value(row, ["insurance_salary", "social_insurance_salary"]) or "0",
        "insurance_employee_rate": get_header_value(row, ["insurance_employee_rate", "employee_insurance_rate"]) or "11",
        "insurance_employer_rate": get_header_value(row, ["insurance_employer_rate", "employer_insurance_rate"]) or "18.75",
        "expected_daily_hours": get_header_value(row, ["expected_daily_hours", "daily_hours"]) or "8",
        "is_active": get_header_value(row, ["is_active", "active", "status"]) or "1",
    }


def parse_csv_rows(file_bytes):
    text = file_bytes.decode("utf-8-sig", errors="ignore")
    reader = csv.DictReader(io.StringIO(text))
    return [dict(r) for r in reader]


def parse_xlsx_rows(file_bytes):
    if load_workbook is None:
        raise Exception("Excel import is not available right now.")

    workbook = load_workbook(io.BytesIO(file_bytes), data_only=True)
    sheet = workbook.active
    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        return []

    headers = [safe(h).lower() for h in rows[0]]
    result = []
    for data_row in rows[1:]:
        item = {}
        for i, header in enumerate(headers):
            if not header:
                continue
            item[header] = "" if i >= len(data_row) or data_row[i] is None else str(data_row[i])
        result.append(item)
    return result


ensure_employees_table()


@router.get("/ui/hr/employees", response_class=HTMLResponse)
def employees_list(request: Request):
    ensure_employees_table()
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT e.*, c.name AS category_name
        FROM employees e
        LEFT JOIN employee_categories c ON c.id = e.category_id
        ORDER BY id DESC
        """
    ).fetchall()
    conn.close()

    msg = safe(request.query_params.get("msg"))
    msg_html = f'<div class="msg success">{escape(msg)}</div>' if msg else ""

    body = ""
    for r in rows:
        total_package = (
            float(r["basic_salary"] or 0)
            + float(r["housing_allowance"] or 0)
            + float(r["transport_allowance"] or 0)
            + float(r["other_allowance"] or 0)
        )
        status_html = '<span class="status-chip green">Active</span>' if int(r["is_active"] or 0) == 1 else '<span class="status-chip gray">Inactive</span>'
        body += f"""
        <tr>
            <td>{escape(safe(r['code']))}</td>
            <td>{escape(safe(r['biometric_code']))}</td>
            <td>{escape(safe(r['name']))}</td>
            <td>{escape(safe(r['category_name']))}</td>
            <td>{escape(safe(r['department']))}</td>
            <td>{escape(safe(r['job_title']))}</td>
            <td>{escape(safe(r['hire_date']))}</td>
            <td class="number-cell">{money(r['basic_salary'])}</td>
            <td class="number-cell">{money(r['insurance_salary'])}</td>
            <td class="number-cell">{money(total_package)}</td>
            <td>{status_html}</td>
            <td><a class="btn blue" href="/ui/hr/employees/{r['id']}/edit">Edit</a></td>
        </tr>
        """

    if not body:
        body = "<tr><td colspan='12' style='text-align:center;'>No employees found.</td></tr>"

    html = f"""
    <div class="card">
        {msg_html}
        <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;">
            <h2>Employees</h2>
            <div style="display:flex;gap:8px;flex-wrap:wrap;">
                <a class="btn gray" href="/ui/hr/categories">Employee Categories</a>
                <a class="btn blue" href="/ui/hr/employees/template.csv">Template CSV</a>
                <a class="btn blue" href="/ui/hr/employees/template.xlsx">Template Excel</a>
                <a class="btn green" href="/ui/hr/employees/new">+ New Employee</a>
            </div>
        </div>

        <form method="post" action="/ui/hr/employees/import" enctype="multipart/form-data" style="margin-top:14px;">
            <div class="row">
                <div class="col">
                    <label>Import Employees (CSV / XLSX)</label>
                    <input type="file" name="file" accept=".csv,.xlsx" required>
                </div>
                <div class="col" style="display:flex;align-items:end;">
                    <button class="btn green" type="submit">Import</button>
                </div>
            </div>
        </form>
    </div>

    <div class="card">
        <p class="section-note">Link each employee to a category so attendance role, shift timing, grace minutes, and overtime policy can be applied automatically during attendance import and payroll processing.</p>
    </div>

    <div class="card">
        <table>
            <tr>
                <th>Code</th>
                <th>Biometric</th>
                <th>Name</th>
                <th>Category</th>
                <th>Department</th>
                <th>Job Title</th>
                <th>Hire Date</th>
                <th>Basic Salary</th>
                <th>Insurance Salary</th>
                <th>Total Package</th>
                <th>Status</th>
                <th>Actions</th>
            </tr>
            {body}
        </table>
    </div>
    """
    return HTMLResponse(render_page("Employees", html, "en", current_path=request.url.path))


@router.get("/ui/hr/employees/new", response_class=HTMLResponse)
def new_employee(request: Request):
    html = employee_form_html("/ui/hr/employees/new")
    return HTMLResponse(render_page("New Employee", html, "en", current_path=request.url.path))


@router.post("/ui/hr/employees/new")
def create_employee(
    code: str = Form(""),
    category_id: str = Form(""),
    biometric_code: str = Form(""),
    name: str = Form(...),
    phone: str = Form(""),
    email: str = Form(""),
    department: str = Form(""),
    job_title: str = Form(""),
    hire_date: str = Form(""),
    national_id: str = Form(""),
    payment_method: str = Form("bank_transfer"),
    bank_name: str = Form(""),
    bank_account: str = Form(""),
    basic_salary: str = Form("0"),
    housing_allowance: str = Form("0"),
    transport_allowance: str = Form("0"),
    other_allowance: str = Form("0"),
    insurance_applicable: int = Form(1),
    insurance_number: str = Form(""),
    insurance_salary: str = Form("0"),
    insurance_employee_rate: str = Form("11"),
    insurance_employer_rate: str = Form("18.75"),
    expected_daily_hours: str = Form("8"),
    is_active: int = Form(1),
):
    ensure_employees_table()
    conn = get_conn()
    employee_code = safe(code) or next_employee_code()

    conn.execute(
        """
        INSERT INTO employees (
            code, category_id, biometric_code, name, phone, email, department, job_title, hire_date, national_id,
            payment_method, bank_name, bank_account,
            basic_salary, housing_allowance, transport_allowance, other_allowance,
            insurance_applicable, insurance_number, insurance_salary, insurance_employee_rate, insurance_employer_rate,
            expected_daily_hours, is_active
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            employee_code,
            int(category_id) if safe(category_id).isdigit() else None,
            safe(biometric_code),
            safe(name),
            safe(phone),
            safe(email),
            safe(department),
            safe(job_title),
            safe(hire_date),
            safe(national_id),
            safe(payment_method) or "bank_transfer",
            safe(bank_name),
            safe(bank_account),
            to_float(basic_salary),
            to_float(housing_allowance),
            to_float(transport_allowance),
            to_float(other_allowance),
            int(insurance_applicable or 0),
            safe(insurance_number),
            to_float(insurance_salary),
            to_float(insurance_employee_rate),
            to_float(insurance_employer_rate),
            to_float(expected_daily_hours, 8),
            int(is_active or 0),
        ),
    )
    conn.commit()
    conn.close()
    return RedirectResponse("/ui/hr/employees", status_code=302)


@router.get("/ui/hr/employees/{employee_id}/edit", response_class=HTMLResponse)
def edit_employee(request: Request, employee_id: int):
    ensure_employees_table()
    conn = get_conn()
    row = conn.execute("SELECT * FROM employees WHERE id = ? LIMIT 1", (employee_id,)).fetchone()
    conn.close()

    if not row:
        return HTMLResponse("Employee not found", status_code=404)

    html = employee_form_html(f"/ui/hr/employees/{employee_id}/edit", dict(row))
    return HTMLResponse(render_page("Edit Employee", html, "en", current_path=request.url.path))


@router.post("/ui/hr/employees/{employee_id}/edit")
def update_employee(
    employee_id: int,
    code: str = Form(""),
    category_id: str = Form(""),
    biometric_code: str = Form(""),
    name: str = Form(...),
    phone: str = Form(""),
    email: str = Form(""),
    department: str = Form(""),
    job_title: str = Form(""),
    hire_date: str = Form(""),
    national_id: str = Form(""),
    payment_method: str = Form("bank_transfer"),
    bank_name: str = Form(""),
    bank_account: str = Form(""),
    basic_salary: str = Form("0"),
    housing_allowance: str = Form("0"),
    transport_allowance: str = Form("0"),
    other_allowance: str = Form("0"),
    insurance_applicable: int = Form(1),
    insurance_number: str = Form(""),
    insurance_salary: str = Form("0"),
    insurance_employee_rate: str = Form("11"),
    insurance_employer_rate: str = Form("18.75"),
    expected_daily_hours: str = Form("8"),
    is_active: int = Form(1),
):
    ensure_employees_table()
    conn = get_conn()
    current_row = conn.execute("SELECT code FROM employees WHERE id = ? LIMIT 1", (employee_id,)).fetchone()
    if not current_row:
        conn.close()
        return HTMLResponse("Employee not found", status_code=404)

    employee_code = safe(code) or safe(current_row["code"]) or next_employee_code()

    conn.execute(
        """
        UPDATE employees
        SET code = ?,
            category_id = ?,
            biometric_code = ?,
            name = ?,
            phone = ?,
            email = ?,
            department = ?,
            job_title = ?,
            hire_date = ?,
            national_id = ?,
            payment_method = ?,
            bank_name = ?,
            bank_account = ?,
            basic_salary = ?,
            housing_allowance = ?,
            transport_allowance = ?,
            other_allowance = ?,
            insurance_applicable = ?,
            insurance_number = ?,
            insurance_salary = ?,
            insurance_employee_rate = ?,
            insurance_employer_rate = ?,
            expected_daily_hours = ?,
            is_active = ?
        WHERE id = ?
        """,
        (
            employee_code,
            int(category_id) if safe(category_id).isdigit() else None,
            safe(biometric_code),
            safe(name),
            safe(phone),
            safe(email),
            safe(department),
            safe(job_title),
            safe(hire_date),
            safe(national_id),
            safe(payment_method) or "bank_transfer",
            safe(bank_name),
            safe(bank_account),
            to_float(basic_salary),
            to_float(housing_allowance),
            to_float(transport_allowance),
            to_float(other_allowance),
            int(insurance_applicable or 0),
            safe(insurance_number),
            to_float(insurance_salary),
            to_float(insurance_employee_rate),
            to_float(insurance_employer_rate),
            to_float(expected_daily_hours, 8),
            int(is_active or 0),
            employee_id,
        ),
    )
    conn.commit()
    conn.close()

    return RedirectResponse("/ui/hr/employees", status_code=302)


@router.get("/ui/hr/employees/template.csv")
def employees_template_csv():
    headers = [
        "code",
        "category_id",
        "category_code",
        "category_name",
        "biometric_code",
        "name",
        "phone",
        "email",
        "department",
        "job_title",
        "hire_date",
        "national_id",
        "payment_method",
        "bank_name",
        "bank_account",
        "basic_salary",
        "housing_allowance",
        "transport_allowance",
        "other_allowance",
        "insurance_applicable",
        "insurance_number",
        "insurance_salary",
        "insurance_employee_rate",
        "insurance_employer_rate",
        "expected_daily_hours",
        "is_active",
    ]
    rows = [
        ["EMP-0001", "", "CAT-OFF", "Office Staff", "1001", "Ahmed Ali", "01000000000", "ahmed@company.com", "Finance", "Accountant", "2026-01-01", "29801011234567", "bank_transfer", "CIB", "00123456789", "12000", "2500", "1500", "500", "1", "INS-1001", "12000", "11", "18.75", "8", "1"],
        ["EMP-0002", "", "CAT-MGT", "Management", "1002", "Mona Salah", "01000000001", "mona@company.com", "HR", "HR Specialist", "2026-02-01", "29802021234567", "cash", "", "", "9000", "1500", "1000", "0", "1", "INS-1002", "9000", "11", "18.75", "8", "1"],
    ]
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)

    data = output.getvalue().encode("utf-8-sig")
    stream = io.BytesIO(data)
    stream.seek(0)
    return StreamingResponse(
        stream,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="employees_template.csv"'},
    )


@router.get("/ui/hr/employees/template.xlsx")
def employees_template_xlsx():
    if Workbook is None:
        return RedirectResponse("/ui/hr/employees?msg=" + quote("Excel template is not available. Use CSV template."))

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Employees Template"
    headers = [
        "code",
        "category_id",
        "category_code",
        "category_name",
        "biometric_code",
        "name",
        "phone",
        "email",
        "department",
        "job_title",
        "hire_date",
        "national_id",
        "payment_method",
        "bank_name",
        "bank_account",
        "basic_salary",
        "housing_allowance",
        "transport_allowance",
        "other_allowance",
        "insurance_applicable",
        "insurance_number",
        "insurance_salary",
        "insurance_employee_rate",
        "insurance_employer_rate",
        "expected_daily_hours",
        "is_active",
    ]
    sheet.append(headers)
    sheet.append(["EMP-0001", "", "CAT-OFF", "Office Staff", "1001", "Ahmed Ali", "01000000000", "ahmed@company.com", "Finance", "Accountant", "2026-01-01", "29801011234567", "bank_transfer", "CIB", "00123456789", "12000", "2500", "1500", "500", "1", "INS-1001", "12000", "11", "18.75", "8", "1"])
    sheet.append(["EMP-0002", "", "CAT-MGT", "Management", "1002", "Mona Salah", "01000000001", "mona@company.com", "HR", "HR Specialist", "2026-02-01", "29802021234567", "cash", "", "", "9000", "1500", "1000", "0", "1", "INS-1002", "9000", "11", "18.75", "8", "1"])

    lookup_sheet = workbook.create_sheet("Lookups")
    lookup_sheet.append(["payment_method", "is_active"])
    lookup_sheet.append(["bank_transfer", "1"])
    lookup_sheet.append(["cash", "0"])

    stream = io.BytesIO()
    workbook.save(stream)
    stream.seek(0)
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="employees_template.xlsx"'},
    )


@router.post("/ui/hr/employees/import")
async def employees_import(file: UploadFile = File(...)):
    ensure_employees_table()
    filename = safe(file.filename).lower()
    file_bytes = await file.read()

    if not filename:
        return RedirectResponse("/ui/hr/employees?msg=" + quote("Please choose a file to import."), status_code=302)

    try:
        if filename.endswith(".csv"):
            raw_rows = parse_csv_rows(file_bytes)
        elif filename.endswith(".xlsx"):
            raw_rows = parse_xlsx_rows(file_bytes)
        else:
            return RedirectResponse("/ui/hr/employees?msg=" + quote("Only CSV or XLSX files are supported."), status_code=302)
    except Exception as ex:
        return RedirectResponse("/ui/hr/employees?msg=" + quote(f"Import failed: {safe(ex)}"), status_code=302)

    conn = get_conn()
    imported = 0
    skipped = 0
    next_seq = 1
    try:
        existing = conn.execute(
            """
            SELECT code
            FROM employees
            WHERE COALESCE(code, '') <> ''
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
        if existing:
            try:
                next_seq = int(safe(existing["code"]).split("-")[-1]) + 1
            except Exception:
                next_seq = 1

        for raw_row in raw_rows:
            row = normalize_import_row(raw_row)
            if not safe(row["name"]):
                skipped += 1
                continue

            code = safe(row["code"])
            if not code:
                code = f"EMP-{next_seq:04d}"
                next_seq += 1

            exists = conn.execute("SELECT id FROM employees WHERE code = ? LIMIT 1", (code,)).fetchone()
            if exists:
                skipped += 1
                continue

            conn.execute(
                """
                INSERT INTO employees (
                    code, category_id, biometric_code, name, phone, email, department, job_title, hire_date, national_id,
                    payment_method, bank_name, bank_account,
                    basic_salary, housing_allowance, transport_allowance, other_allowance,
                    insurance_applicable, insurance_number, insurance_salary, insurance_employee_rate, insurance_employer_rate,
                    expected_daily_hours, is_active
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    code,
                    resolve_category_id(conn, row["category_id"], row["category_code"], row["category_name"]),
                    safe(row["biometric_code"]),
                    safe(row["name"]),
                    safe(row["phone"]),
                    safe(row["email"]),
                    safe(row["department"]),
                    safe(row["job_title"]),
                    safe(row["hire_date"]),
                    safe(row["national_id"]),
                    safe(row["payment_method"]) or "bank_transfer",
                    safe(row["bank_name"]),
                    safe(row["bank_account"]),
                    to_float(row["basic_salary"]),
                    to_float(row["housing_allowance"]),
                    to_float(row["transport_allowance"]),
                    to_float(row["other_allowance"]),
                    to_int_flag(row["insurance_applicable"], 1),
                    safe(row["insurance_number"]),
                    to_float(row["insurance_salary"]),
                    to_float(row["insurance_employee_rate"], 11),
                    to_float(row["insurance_employer_rate"], 18.75),
                    to_float(row["expected_daily_hours"], 8),
                    to_int_flag(row["is_active"], 1),
                ),
            )
            imported += 1

        conn.commit()
    finally:
        conn.close()

    return RedirectResponse(
        "/ui/hr/employees?msg=" + quote(f"Employees imported: {imported}. Skipped: {skipped}."),
        status_code=302,
    )
