from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from auth import can
from db import get_conn
from i18n import get_lang
from layout import render_page
from modules.accounting.accounting_engine import create_journal_entry, post_journal_entry, submit_journal_for_final_post, reverse_journal_entry
from modules.accounting.allocation_engine import (
    delete_payment_allocations,
    get_allocated_total_for_payment,
    get_payment_allocations,
    get_payment_unallocated_amount,
    refresh_customer_invoice_payment_status,
    refresh_vendor_bill_payment_status,
)

try:
    from modules.accounting.config import get_setting_value
except Exception:
    def get_setting_value(key, default=None):
        defaults = {
            "default_cash_account": "111100",
            "default_bank_account": "111150",
            "customer_control_account": "112100",
            "vendor_control_account": "211100",
        }
        return defaults.get(key, default)


router = APIRouter()


def accounting_allowed(request: Request, action: str) -> bool:
    return can(request, "accounting", action)


def permission_denied(en: str, ar: str):
    return HTMLResponse(ar if get_lang_fallback() == "ar" else en, status_code=403)


def get_lang_fallback():
    return "en"


def tr(lang: str, en: str, ar: str) -> str:
    return ar if lang == "ar" else en


def safe(x):
    return "" if x is None else str(x).strip()


def q2(x):
    try:
        return Decimal(str(x if x is not None else 0)).quantize(Decimal("1.00"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0.00")


def money(x):
    try:
        return f"{float(x or 0):,.2f}"
    except Exception:
        return "0.00"


def safe_int(x, default=0):
    try:
        if x is None or str(x).strip() == "":
            return default
        return int(float(x))
    except Exception:
        return default


def ensure_column(conn, table_name, column_name, alter_sql):
    cols = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    names = [c["name"] for c in cols]
    if column_name not in names:
        conn.execute(alter_sql)


def ensure_tables():
    conn = get_conn()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS employee_custody_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_no TEXT,
            request_date TEXT,
            employee_id INTEGER,
            amount REAL DEFAULT 0,
            notes TEXT,
            status TEXT DEFAULT 'active',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cash_vouchers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            voucher_type TEXT NOT NULL,
            voucher_no TEXT,
            voucher_date TEXT,
            party_name TEXT,
            party_type TEXT,
            party_id INTEGER,
            liquidity_account_code TEXT,
            counter_account_code TEXT,
            amount REAL DEFAULT 0,
            description TEXT,
            signature_name TEXT,
            status TEXT DEFAULT 'draft',
            journal_id INTEGER,
            reversed_journal_id INTEGER,
            employee_trans_type TEXT,
            advance_id INTEGER,
            custody_request_id INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    ensure_column(conn, "cash_vouchers", "voucher_type", "ALTER TABLE cash_vouchers ADD COLUMN voucher_type TEXT")
    ensure_column(conn, "cash_vouchers", "voucher_no", "ALTER TABLE cash_vouchers ADD COLUMN voucher_no TEXT")
    ensure_column(conn, "cash_vouchers", "voucher_date", "ALTER TABLE cash_vouchers ADD COLUMN voucher_date TEXT")
    ensure_column(conn, "cash_vouchers", "party_name", "ALTER TABLE cash_vouchers ADD COLUMN party_name TEXT")
    ensure_column(conn, "cash_vouchers", "party_type", "ALTER TABLE cash_vouchers ADD COLUMN party_type TEXT")
    ensure_column(conn, "cash_vouchers", "party_id", "ALTER TABLE cash_vouchers ADD COLUMN party_id INTEGER")
    ensure_column(conn, "cash_vouchers", "liquidity_account_code", "ALTER TABLE cash_vouchers ADD COLUMN liquidity_account_code TEXT")
    ensure_column(conn, "cash_vouchers", "counter_account_code", "ALTER TABLE cash_vouchers ADD COLUMN counter_account_code TEXT")
    ensure_column(conn, "cash_vouchers", "amount", "ALTER TABLE cash_vouchers ADD COLUMN amount REAL DEFAULT 0")
    ensure_column(conn, "cash_vouchers", "description", "ALTER TABLE cash_vouchers ADD COLUMN description TEXT")
    ensure_column(conn, "cash_vouchers", "signature_name", "ALTER TABLE cash_vouchers ADD COLUMN signature_name TEXT")
    ensure_column(conn, "cash_vouchers", "status", "ALTER TABLE cash_vouchers ADD COLUMN status TEXT DEFAULT 'draft'")
    ensure_column(conn, "cash_vouchers", "journal_id", "ALTER TABLE cash_vouchers ADD COLUMN journal_id INTEGER")
    ensure_column(conn, "cash_vouchers", "reversed_journal_id", "ALTER TABLE cash_vouchers ADD COLUMN reversed_journal_id INTEGER")
    ensure_column(conn, "cash_vouchers", "employee_trans_type", "ALTER TABLE cash_vouchers ADD COLUMN employee_trans_type TEXT")
    ensure_column(conn, "cash_vouchers", "advance_id", "ALTER TABLE cash_vouchers ADD COLUMN advance_id INTEGER")
    ensure_column(conn, "cash_vouchers", "custody_request_id", "ALTER TABLE cash_vouchers ADD COLUMN custody_request_id INTEGER")
    ensure_column(conn, "cash_vouchers", "created_at", "ALTER TABLE cash_vouchers ADD COLUMN created_at TEXT DEFAULT CURRENT_TIMESTAMP")
    ensure_column(conn, "employee_custody_requests", "request_no", "ALTER TABLE employee_custody_requests ADD COLUMN request_no TEXT")
    ensure_column(conn, "employee_custody_requests", "request_date", "ALTER TABLE employee_custody_requests ADD COLUMN request_date TEXT")
    ensure_column(conn, "employee_custody_requests", "employee_id", "ALTER TABLE employee_custody_requests ADD COLUMN employee_id INTEGER")
    ensure_column(conn, "employee_custody_requests", "amount", "ALTER TABLE employee_custody_requests ADD COLUMN amount REAL DEFAULT 0")
    ensure_column(conn, "employee_custody_requests", "notes", "ALTER TABLE employee_custody_requests ADD COLUMN notes TEXT")
    ensure_column(conn, "employee_custody_requests", "status", "ALTER TABLE employee_custody_requests ADD COLUMN status TEXT DEFAULT 'active'")
    ensure_column(conn, "employee_custody_requests", "created_at", "ALTER TABLE employee_custody_requests ADD COLUMN created_at TEXT DEFAULT CURRENT_TIMESTAMP")
    conn.commit()
    conn.close()


ensure_tables()


def route_base(voucher_type: str) -> str:
    return "/ui/accounting/cash-receipts" if voucher_type == "receipt" else "/ui/accounting/cash-payments"


def voucher_title(lang: str, voucher_type: str) -> str:
    return tr(lang, "Cash Receipt Voucher", "سند قبض نقدي") if voucher_type == "receipt" else tr(lang, "Cash Payment Voucher", "سند صرف نقدي")


def voucher_list_title(lang: str, voucher_type: str) -> str:
    return tr(lang, "Cash Receipts", "سندات القبض") if voucher_type == "receipt" else tr(lang, "Cash Payments", "سندات الصرف")


def party_label(lang: str, voucher_type: str) -> str:
    return tr(lang, "Received From", "استلمنا من") if voucher_type == "receipt" else tr(lang, "Paid To", "تم الصرف إلى")


def signature_label(lang: str, voucher_type: str) -> str:
    return tr(lang, "Received By / Depositor", "اسم المسلم") if voucher_type == "receipt" else tr(lang, "Received By", "اسم المستلم")


def next_voucher_no(voucher_type: str) -> str:
    prefix = "CRV" if voucher_type == "receipt" else "CPV"
    conn = get_conn()
    row = conn.execute(
        """
        SELECT voucher_no
        FROM cash_vouchers
        WHERE voucher_type = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (voucher_type,),
    ).fetchone()
    conn.close()
    if not row or not row["voucher_no"]:
        return f"{prefix}-0001"
    try:
        num = int(str(row["voucher_no"]).split("-")[-1])
    except Exception:
        num = 0
    return f"{prefix}-{num + 1:04d}"


def liquidity_account_options(selected_code=""):
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT code, name
        FROM accounts
        WHERE COALESCE(is_active,1)=1
          AND COALESCE(is_group,0)=0
          AND COALESCE(allow_posting,1)=1
        ORDER BY code, name
        """
    ).fetchall()
    conn.close()
    default_cash = safe(get_setting_value("default_cash_account", "111100"))
    default_bank = safe(get_setting_value("default_bank_account", "111150"))
    html = '<option value="">-- Select Liquidity Account --</option>'
    for row in rows:
        code = safe(row["code"])
        name = safe(row["name"]).lower()
        if code not in (default_cash, default_bank) and "cash" not in name and "bank" not in name:
            continue
        sel = "selected" if code == safe(selected_code) else ""
        html += f'<option value="{code}" {sel}>{code} - {safe(row["name"])}</option>'
    return html


def counter_account_options(selected_code=""):
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT code, name
        FROM accounts
        WHERE COALESCE(is_active,1)=1
          AND COALESCE(is_group,0)=0
          AND COALESCE(allow_posting,1)=1
        ORDER BY code, name
        """
    ).fetchall()
    conn.close()
    html = '<option value="">-- Select Account --</option>'
    for row in rows:
        code = safe(row["code"])
        sel = "selected" if code == safe(selected_code) else ""
        html += f'<option value="{code}" {sel}>{code} - {safe(row["name"])}</option>'
    return html


def account_display(code):
    if not code:
        return ""
    conn = get_conn()
    row = conn.execute("SELECT code, name FROM accounts WHERE code = ? LIMIT 1", (safe(code),)).fetchone()
    conn.close()
    if row:
        return f"{safe(row['code'])} - {safe(row['name'])}"
    return safe(code)


def get_partner_rows(party_type: str):
    party_type = safe(party_type).lower()
    if party_type == "employee":
        conn = get_conn()
        rows = conn.execute(
            """
            SELECT id, code, name, '' AS account_code
            FROM employees
            WHERE COALESCE(is_active,1)=1
            ORDER BY name
            """
        ).fetchall()
        conn.close()
        return rows
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT id, code, name, account_code
        FROM partners
        WHERE LOWER(COALESCE(partner_type,'')) = ?
          AND COALESCE(is_active,1)=1
        ORDER BY name
        """,
        (safe(party_type).lower(),),
    ).fetchall()
    conn.close()
    return rows


def linked_party_options(lang: str, party_type: str, selected_id=""):
    selected_id = safe(selected_id)
    if party_type == "employee":
        conn = get_conn()
        rows = conn.execute("SELECT id, code, name FROM employees WHERE COALESCE(is_active,1)=1 ORDER BY name").fetchall()
        conn.close()
        html = f'<option value="">-- {tr(lang, "Select Employee", "اختر الموظف")} --</option>'
        for row in rows:
            option_label = f"{safe(row['code'])} - {safe(row['name'])}" if safe(row["code"]) else safe(row["name"])
            sel = "selected" if selected_id == str(row["id"]) else ""
            html += f'<option value="{row["id"]}" {sel}>{option_label}</option>'
        return html

    label = tr(lang, "Customer", "عميل") if party_type == "customer" else tr(lang, "Vendor", "مورد")
    html = f'<option value="">-- Select {label} --</option>'
    for row in get_partner_rows(party_type):
        option_label = f"{safe(row['code'])} - {safe(row['name'])}" if safe(row["code"]) else safe(row["name"])
        sel = "selected" if selected_id == str(row["id"]) else ""
        html += f'<option value="{row["id"]}" {sel}>{option_label}</option>'
    return html


@router.get("/ui/accounting/api/employee-advances/{employee_id}")
def get_employee_advances_api(request: Request, employee_id: int):
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT id, advance_no, amount, installment_amount, advance_date, notes, status
        FROM employee_advances
        WHERE employee_id = ?
          AND LOWER(COALESCE(status, 'active')) = 'active'
        ORDER BY advance_date DESC
        """,
        (employee_id,),
    ).fetchall()
    conn.close()
    return [
        {
            "id": r["id"],
            "no": r["advance_no"],
            "amount": r["amount"],
            "installment": r["installment_amount"],
            "date": r["advance_date"],
            "notes": r["notes"],
            "status": "pending",
        }
        for r in rows
    ]


@router.get("/ui/accounting/api/employee-custody-requests/{employee_id}")
def get_employee_custody_requests_api(request: Request, employee_id: int):
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT id, request_no, request_date, amount, notes, status
        FROM employee_custody_requests
        WHERE employee_id = ?
          AND LOWER(COALESCE(status, 'active')) = 'active'
          AND NOT EXISTS (
              SELECT 1
              FROM cash_vouchers v
              WHERE COALESCE(v.custody_request_id, 0) = employee_custody_requests.id
                AND LOWER(COALESCE(v.voucher_type,'')) = 'payment'
                AND LOWER(COALESCE(v.employee_trans_type,'')) = 'custody'
                AND LOWER(COALESCE(v.status,'')) <> 'reversed'
          )
        ORDER BY request_date DESC, id DESC
        """,
        (employee_id,),
    ).fetchall()
    conn.close()
    return [
        {
            "id": r["id"],
            "no": r["request_no"],
            "amount": r["amount"],
            "date": r["request_date"],
            "notes": r["notes"],
            "status": "pending",
        }
        for r in rows
    ]


def get_partner(conn, party_type: str, party_id):
    party_type = safe(party_type).lower()
    party_id = safe_int(party_id)
    if party_type not in ("customer", "vendor") or party_id <= 0:
        return None
    return conn.execute(
        """
        SELECT *
        FROM partners
        WHERE id = ?
          AND LOWER(COALESCE(partner_type,'')) = ?
        LIMIT 1
        """,
        (party_id, party_type),
    ).fetchone()


def default_counter_account_for_party(party_type: str, partner_row=None):
    if partner_row and safe(partner_row["account_code"]):
        return safe(partner_row["account_code"])
    if safe(party_type).lower() == "customer":
        return safe(get_setting_value("customer_control_account", "112100"))
    if safe(party_type).lower() == "vendor":
        return safe(get_setting_value("vendor_control_account", "211100"))
    return ""


def get_voucher(conn, voucher_id: int):
    return conn.execute("SELECT * FROM cash_vouchers WHERE id = ? LIMIT 1", (voucher_id,)).fetchone()


def voucher_payment_type(voucher):
    if not voucher:
        return ""
    voucher_type = safe(voucher["voucher_type"]).lower()
    party_type = safe(voucher["party_type"]).lower()
    if voucher_type == "receipt" and party_type == "customer" and safe_int(voucher["party_id"]) > 0:
        return "cash_receipt"
    if voucher_type == "payment" and party_type == "vendor" and safe_int(voucher["party_id"]) > 0:
        return "cash_payment"
    return ""


def allocation_rows_for_voucher(conn, voucher):
    payment_type = voucher_payment_type(voucher)
    if not payment_type:
        return []
    rows = get_payment_allocations(conn, payment_type, voucher["id"])
    result = []
    for row in rows:
        item = dict(row)
        if safe(row["document_type"]) == "customer_invoice":
            doc = conn.execute(
                "SELECT invoice_no AS doc_no, invoice_date AS doc_date, net_amount FROM customer_invoices WHERE id = ? LIMIT 1",
                (row["document_id"],),
            ).fetchone()
            item["open_url"] = f"/ui/accounting/customer-invoices/{row['document_id']}/view"
        elif safe(row["document_type"]) == "vendor_bill":
            doc = conn.execute(
                "SELECT bill_no AS doc_no, bill_date AS doc_date, net_amount FROM vendor_bills WHERE id = ? LIMIT 1",
                (row["document_id"],),
            ).fetchone()
            item["open_url"] = f"/ui/accounting/vendor-bills/{row['document_id']}/view"
        else:
            doc = None
            item["open_url"] = "#"
        item["doc_no"] = safe(doc["doc_no"]) if doc else ""
        item["doc_date"] = safe(doc["doc_date"]) if doc else ""
        item["doc_total"] = doc["net_amount"] if doc else 0
        result.append(item)
    return result


def validate_voucher(voucher_date, party_name, party_type, party_id, liquidity_account_code, counter_account_code, amount):
    if not safe(voucher_date):
        raise Exception("Voucher date is required")
    if not safe(party_name):
        raise Exception("Party name is required")
    if safe(party_type).lower() in ("customer", "vendor") and safe_int(party_id) <= 0:
        raise Exception("Linked customer/vendor is required")
    if not safe(liquidity_account_code):
        raise Exception("Liquidity account is required")
    if not safe(counter_account_code):
        raise Exception("Counter account is required")
    if q2(amount) <= Decimal("0.00"):
        raise Exception("Amount must be greater than zero")


def build_lines(voucher):
    amount = q2(voucher["amount"])
    description = safe(voucher["description"]) or f"{safe(voucher['voucher_no'])} - {safe(voucher['party_name'])}"
    party_type = safe(voucher["party_type"]).lower()
    partner_type = party_type if party_type in ("customer", "vendor", "employee") else None
    partner_id = safe_int(voucher["party_id"]) or None
    if safe(voucher["voucher_type"]) == "receipt":
        return [
            {"description": description, "account_code": safe(voucher["liquidity_account_code"]), "debit": amount, "credit": Decimal("0.00"), "partner_type": None, "partner_id": None},
            {"description": description, "account_code": safe(voucher["counter_account_code"]), "debit": Decimal("0.00"), "credit": amount, "partner_type": partner_type, "partner_id": partner_id},
        ]
    return [
        {"description": description, "account_code": safe(voucher["counter_account_code"]), "debit": amount, "credit": Decimal("0.00"), "partner_type": partner_type, "partner_id": partner_id},
        {"description": description, "account_code": safe(voucher["liquidity_account_code"]), "debit": Decimal("0.00"), "credit": amount, "partner_type": None, "partner_id": None},
    ]


def create_draft_journal(conn, voucher_id: int):
    voucher = get_voucher(conn, voucher_id)
    if not voucher:
        raise Exception("Voucher not found")
    journal_id = create_journal_entry(
        conn=conn,
        entry_date=safe(voucher["voucher_date"]),
        description=safe(voucher["description"]) or f"{safe(voucher['voucher_no'])} - {safe(voucher['party_name'])}",
        reference=safe(voucher["voucher_no"]),
        source_type="cash_voucher",
        source_id=voucher_id,
        lines=build_lines(voucher),
    )
    conn.execute("UPDATE cash_vouchers SET journal_id = ?, status = 'draft' WHERE id = ?", (journal_id, voucher_id))
    return journal_id


def amount_in_words(amount) -> str:
    return f"{money(amount)} EGP"


def party_type_select_html(lang: str, selected="other"):
    selected = safe(selected).lower() or "other"
    options = [
        ("other", "Other", "أخرى"),
        ("customer", "Customer", "عميل"),
        ("vendor", "Vendor", "مورد"),
        ("employee", "Employee", "موظف"),
    ]
    html = ""
    for value, en, ar in options:
        sel = "selected" if selected == value else ""
        html += f'<option value="{value}" {sel}>{tr(lang, en, ar)}</option>'
    return html


def render_form(lang: str, voucher_type: str, action_url: str, values=None, error=""):
    values = values or {}
    error_html = f'<div class="msg error">{error}</div>' if error else ""
    party_type = safe(values.get("party_type")).lower() or "other"
    manual_party_display = "block" if party_type not in ("customer", "vendor", "employee") else "none"
    customer_display = "block" if party_type == "customer" else "none"
    vendor_display = "block" if party_type == "vendor" else "none"
    employee_display = "block" if party_type == "employee" else "none"
    
    trans_type = safe(values.get("employee_trans_type")).lower()
    advance_select_display = "block" if party_type == "employee" and trans_type == "advance" else "none"
    custody_select_display = "block" if party_type == "employee" and trans_type == "custody" else "none"
    employee_counter_account = (
        safe(get_setting_value("employee_custody_account", "112200"))
        if trans_type == "custody"
        else safe(get_setting_value("employee_advance_account", "121200"))
    )
    counter_select_display = "none" if party_type == "employee" else "block"
    employee_counter_display = "block" if party_type == "employee" else "none"

    return f"""
    <div class="card">
        {error_html}
        <h2>{voucher_title(lang, voucher_type)}</h2>
        <div class="msg info" style="margin-bottom:14px;">
            {tr(lang, 'Use customer/vendor cash vouchers to record the actual cash movement first, then allocate the unallocated balance to invoices or bills.', 'سجل حركة النقدية أولًا من هنا، وبعد الترحيل استخدم الرصيد غير المخصص لتسوية الفواتير أو جزئيًا.')}
        </div>
        <form method="post" action="{action_url}">
            <div class="row">
                <div class="col">
                    <label>{tr(lang, 'Voucher No', 'رقم السند')}</label>
                    <input name="voucher_no" value="{safe(values.get('voucher_no') or next_voucher_no(voucher_type))}" readonly>
                </div>
                <div class="col">
                    <label>{tr(lang, 'Date', 'التاريخ')}</label>
                    <input type="date" name="voucher_date" value="{safe(values.get('voucher_date'))}" required>
                </div>
            </div>
            <div class="row" style="margin-top:14px;">
                <div class="col" id="manual_party_wrap" style="display:{manual_party_display};">
                    <label>{party_label(lang, voucher_type)}</label>
                    <input name="party_name" value="{safe(values.get('party_name'))}">
                </div>
                <div class="col">
                    <label>{tr(lang, 'Party Type', 'نوع الطرف')}</label>
                    <select name="party_type" id="party_type" onchange="toggleLinkedPartyFields()">
                        {party_type_select_html(lang, party_type)}
                    </select>
                </div>
            </div>
            <div class="row" style="margin-top:14px;">
                <div class="col" id="customer_party_wrap" style="display:{customer_display};">
                    <label>{tr(lang, 'Linked Customer', 'العميل المرتبط')}</label>
                    <select name="customer_id" id="customer_id" onchange="syncLinkedPartyName()">
                        {linked_party_options(lang, 'customer', values.get('party_id') if party_type == 'customer' else '')}
                    </select>
                </div>
                <div class="col" id="vendor_party_wrap" style="display:{vendor_display};">
                    <label>{tr(lang, 'Linked Vendor', 'المورد المرتبط')}</label>
                    <select name="vendor_id" id="vendor_id" onchange="syncLinkedPartyName()">
                        {linked_party_options(lang, 'vendor', values.get('party_id') if party_type == 'vendor' else '')}
                    </select>
                </div>
                <div class="col" id="employee_party_wrap" style="display:{employee_display};">
                    <label>{tr(lang, 'Linked Employee', 'الموظف المرتبط')}</label>
                    <div style="display:flex; gap:8px;">
                        <select name="employee_id" id="employee_id" style="flex:1;" onchange="syncLinkedPartyName(); updateEmployeeAdvances();">
                            {linked_party_options(lang, 'employee', values.get('party_id') if party_type == 'employee' else '')}
                        </select>
                        <a id="employee_statement_link" class="btn blue" style="padding: 8px 12px; display: {employee_display};" href="#" target="_blank">
                            {tr(lang, "Statement", "كشف الحساب")}
                        </a>
                    </div>
                </div>
            </div>
            
            <div id="employee_extra_fields" style="display:{employee_display}; border:1px solid #eee; padding:10px; border-radius:4px; margin-top:14px; background:#f9f9f9;">
                <div class="row">
                    <div class="col">
                        <label>{tr(lang, 'Transaction Type', 'نوع العملية')}</label>
                        <select name="employee_trans_type" id="employee_trans_type" onchange="updateEmployeeAdvances()">
                            <option value="" {"selected" if trans_type not in ("advance", "custody") else ""}>-- {tr(lang, "Select Transaction Type", "اختر نوع العملية")} --</option>
                            <option value="advance" {"selected" if trans_type == "advance" else ""}>{tr(lang, "Advance", "سلفة")}</option>
                            <option value="custody" {"selected" if trans_type == "custody" else ""}>{tr(lang, "Custody", "عهدة")}</option>
                        </select>
                    </div>
                    <div class="col" id="advance_select_wrap" style="display:{advance_select_display};">
                        <label>{tr(lang, 'Select Advance Request', 'اختر طلب السلفة')}</label>
                        <select name="advance_id" id="advance_id" onchange="syncAdvanceAmount()">
                            <option value="">-- {tr(lang, "Select Advance", "اختر السلفة")} --</option>
                        </select>
                    </div>
                    <div class="col" id="custody_select_wrap" style="display:{custody_select_display};">
                        <label>{tr(lang, 'Select Custody Request', 'اختر طلب العهدة')}</label>
                        <select name="custody_request_id" id="custody_request_id" onchange="syncCustodyAmount()">
                            <option value="">-- {tr(lang, "Select Custody Request", "اختر طلب العهدة")} --</option>
                        </select>
                    </div>
                </div>
            </div>

            <div class="row" style="margin-top:14px;">
                <div class="col">
                    <label>{tr(lang, 'Cash / Bank Account', 'حساب النقدية / البنك')}</label>
                    <select name="liquidity_account_code" required>
                        {liquidity_account_options(values.get('liquidity_account_code') or safe(get_setting_value('default_cash_account', '111100')))}
                    </select>
                </div>
                <div class="col" id="counter_account_wrap" style="display:{counter_select_display};">
                    <label>{tr(lang, 'Counter Account', 'الحساب المقابل')}</label>
                    <select id="counter_account_code_select" name="counter_account_code" required>
                        {counter_account_options(values.get('counter_account_code'))}
                    </select>
                </div>
                <div class="col" id="employee_counter_wrap" style="display:{employee_counter_display};">
                    <label>{tr(lang, 'Counter Account', 'الحساب المقابل')}</label>
                    <input id="employee_counter_account_value" value="{employee_counter_account}" readonly>
                </div>
            </div>
            <div class="row" style="margin-top:14px;">
                <div class="col">
                    <label>{tr(lang, 'Amount', 'المبلغ')}</label>
                    <input type="number" step="0.01" min="0" name="amount" value="{safe(values.get('amount'))}" required>
                </div>
                <div class="col">
                    <label>{signature_label(lang, voucher_type)}</label>
                    <input name="signature_name" value="{safe(values.get('signature_name'))}">
                </div>
            </div>
            <div class="row" style="margin-top:14px;">
                <div class="col">
                    <label>{tr(lang, 'Description', 'البيان')}</label>
                    <input name="description" value="{safe(values.get('description'))}">
                </div>
            </div>
            <div style="margin-top:18px;">
                <button class="btn green" type="submit">{tr(lang, 'Save Draft', 'حفظ كمسودة')}</button>
                <a class="btn gray" href="{route_base(voucher_type)}">{tr(lang, 'Back', 'رجوع')}</a>
            </div>
        </form>
        <script>
        function toggleLinkedPartyFields() {{
            const type = document.getElementById('party_type')?.value || 'other';
            const transType = document.getElementById('employee_trans_type')?.value || '';
            const manualWrap = document.getElementById('manual_party_wrap');
            const customerWrap = document.getElementById('customer_party_wrap');
            const vendorWrap = document.getElementById('vendor_party_wrap');
            const employeeWrap = document.getElementById('employee_party_wrap');
            const employeeExtra = document.getElementById('employee_extra_fields');
            const employeeStatementLink = document.getElementById('employee_statement_link');
            const counterWrap = document.getElementById('counter_account_wrap');
            const employeeCounterWrap = document.getElementById('employee_counter_wrap');
            const counterSelect = document.getElementById('counter_account_code_select');
            const employeeCounterValue = document.getElementById('employee_counter_account_value');

            if (manualWrap) manualWrap.style.display = (type === 'customer' || type === 'vendor' || type === 'employee') ? 'none' : 'block';
            if (customerWrap) customerWrap.style.display = type === 'customer' ? 'block' : 'none';
            if (vendorWrap) vendorWrap.style.display = type === 'vendor' ? 'block' : 'none';
            if (employeeWrap) employeeWrap.style.display = type === 'employee' ? 'block' : 'none';
            if (employeeExtra) employeeExtra.style.display = type === 'employee' ? 'block' : 'none';
            if (employeeStatementLink) employeeStatementLink.style.display = type === 'employee' ? 'block' : 'none';
            if (counterWrap) counterWrap.style.display = type === 'employee' ? 'none' : 'block';
            if (employeeCounterWrap) employeeCounterWrap.style.display = type === 'employee' ? 'block' : 'none';
            if (counterSelect) {{
                if (type === 'employee') {{
                    if (employeeCounterValue && employeeCounterValue.value) {{
                        counterSelect.value = employeeCounterValue.value;
                    }}
                    counterSelect.required = false;
                }} else {{
                    counterSelect.required = true;
                }}
            }}
            syncEmployeeAmountLock(type, transType);
            
            if (type === 'employee') updateEmployeeAdvances();
        }}
        function syncLinkedPartyName() {{
            const type = document.getElementById('party_type')?.value || '';
            const target = document.querySelector('input[name="party_name"]');
            const statementLink = document.getElementById('employee_statement_link');
            if (!target) return;
            let selector = null;
            if (type === 'customer') selector = document.getElementById('customer_id');
            if (type === 'vendor') selector = document.getElementById('vendor_id');
            if (type === 'employee') selector = document.getElementById('employee_id');
            if (!selector) return;
            const option = selector.options[selector.selectedIndex];
            if (option && option.value) {{
                target.value = option.text;
                if (type === 'employee' && statementLink) {{
                    statementLink.href = `/ui/accounting/partner-ledger?partner_type=employee&partner_id=${{option.value}}`;
                }}
            }}
        }}
        
        async function updateEmployeeAdvances() {{
            const empId = document.getElementById('employee_id')?.value;
            const transType = document.getElementById('employee_trans_type')?.value;
            const advanceWrap = document.getElementById('advance_select_wrap');
            const advanceSelect = document.getElementById('advance_id');
            const custodyWrap = document.getElementById('custody_select_wrap');
            const custodySelect = document.getElementById('custody_request_id');
            const preSelectedAdvanceId = "{safe(values.get('advance_id'))}";
            const preSelectedCustodyId = "{safe(values.get('custody_request_id'))}";
            syncEmployeeAmountLock('employee', transType);
            
            if (transType === 'advance' && empId) {{
                advanceWrap.style.display = 'block';
                custodyWrap.style.display = 'none';
                try {{
                    const res = await fetch(`/ui/accounting/api/employee-advances/${{empId}}`);
                    const data = await res.json();
                    advanceSelect.innerHTML = '<option value="">-- {tr(lang, "Select Advance", "اختر السلفة")} --</option>';
                    data.forEach(adv => {{
                        const opt = document.createElement('option');
                        opt.value = adv.id;
                        const installmentText = adv.installment > 0 ? ` - القسط: ${{adv.installment}}` : '';
                        const statusText = adv.status === 'pending' ? ' [Pending]' : '';
                        opt.text = `${{adv.no}} (${{adv.amount}} EGP)${{installmentText}} - ${{adv.date}}${{statusText}}`;
                        opt.dataset.amount = adv.amount;
                        opt.dataset.no = adv.no;
                        opt.dataset.notes = adv.notes || '';
                        if (String(adv.id) === preSelectedAdvanceId) {{
                            opt.selected = true;
                        }}
                        advanceSelect.appendChild(opt);
                    }});
                    if (preSelectedAdvanceId) syncAdvanceAmount();
                }} catch(e) {{ console.error(e); }}
            }} else if (transType === 'custody' && empId) {{
                advanceWrap.style.display = 'none';
                custodyWrap.style.display = 'block';
                try {{
                    const res = await fetch(`/ui/accounting/api/employee-custody-requests/${{empId}}`);
                    const data = await res.json();
                    custodySelect.innerHTML = '<option value="">-- {tr(lang, "Select Custody Request", "اختر طلب العهدة")} --</option>';
                    data.forEach(req => {{
                        const opt = document.createElement('option');
                        opt.value = req.id;
                        const statusText = req.status === 'pending' ? ' [Pending]' : '';
                        opt.text = `${{req.no}} (${{req.amount}} EGP) - ${{req.date}}${{statusText}}`;
                        opt.dataset.amount = req.amount;
                        opt.dataset.no = req.no;
                        opt.dataset.notes = req.notes || '';
                        if (String(req.id) === preSelectedCustodyId) {{
                            opt.selected = true;
                        }}
                        custodySelect.appendChild(opt);
                    }});
                    if (preSelectedCustodyId) syncCustodyAmount();
                }} catch(e) {{ console.error(e); }}
            }} else {{
                advanceWrap.style.display = 'none';
                custodyWrap.style.display = 'none';
            }}
        }}
        
        function syncAdvanceAmount() {{
            const advanceSelect = document.getElementById('advance_id');
            const amountInput = document.querySelector('input[name="amount"]');
            const descInput = document.querySelector('input[name="description"]');
            const empSelect = document.getElementById('employee_id');
            const option = advanceSelect.options[advanceSelect.selectedIndex];
            
            if (option && option.dataset.amount && amountInput) {{
                amountInput.value = option.dataset.amount;
                if (descInput && empSelect && option.value !== '') {{
                    const empName = empSelect.options[empSelect.selectedIndex].text;
                    const advNo = option.dataset.no;
                    const notes = option.dataset.notes;
                    if (descInput.value === '') {{
                        let desc = `صرف سلفة رقم ${{advNo}} للموظف ${{empName}}`;
                        if (notes) desc += ` (${{notes}})`;
                        descInput.value = desc;
                    }}
                }}
            }}
        }}

        function syncCustodyAmount() {{
            const custodySelect = document.getElementById('custody_request_id');
            const amountInput = document.querySelector('input[name="amount"]');
            const descInput = document.querySelector('input[name="description"]');
            const empSelect = document.getElementById('employee_id');
            const option = custodySelect.options[custodySelect.selectedIndex];
            
            if (option && option.dataset.amount && amountInput) {{
                amountInput.value = option.dataset.amount;
                if (descInput && empSelect && option.value !== '') {{
                    const empName = empSelect.options[empSelect.selectedIndex].text;
                    const reqNo = option.dataset.no;
                    const notes = option.dataset.notes;
                    if (descInput.value === '') {{
                        let desc = `صرف عهدة رقم ${{reqNo}} للموظف ${{empName}}`;
                        if (notes) desc += ` (${{notes}})`;
                        descInput.value = desc;
                    }}
                }}
            }}
        }}

        function syncEmployeeAmountLock(partyType, transType) {{
            const amountInput = document.querySelector('input[name="amount"]');
            if (!amountInput) return;
            const isEmployeeRequest = partyType === 'employee' && (transType === 'advance' || transType === 'custody');
            amountInput.readOnly = isEmployeeRequest;
            if (isEmployeeRequest) {{
                amountInput.style.background = '#f3f4f6';
                amountInput.placeholder = "{tr(lang, 'Auto from selected request', 'تلقائي من الطلب المختار')}";
            }} else {{
                amountInput.style.background = '';
                amountInput.placeholder = '';
            }}
        }}

        toggleLinkedPartyFields();
        </script>
    </div>
    """


def list_page(request: Request, voucher_type: str):
    if not accounting_allowed(request, "view"):
        return HTMLResponse("Permission denied", status_code=403)
    lang = get_lang(request)
    conn = get_conn()
    rows = conn.execute("SELECT * FROM cash_vouchers WHERE voucher_type = ? ORDER BY id DESC", (voucher_type,)).fetchall()
    conn.close()
    body = ""
    status_ar = {"draft": "مسودة", "posted": "مرحل", "reversed": "معكوس"}
    for row in rows:
        status = safe(row["status"]).lower()
        status_cls = "green" if status == "posted" else ("red" if status == "reversed" else "orange")
        body += f"""
        <tr>
            <td>{safe(row['voucher_no'])}</td>
            <td>{safe(row['voucher_date'])}</td>
            <td>{safe(row['party_name'])}</td>
            <td>{safe(row['party_type']).title()}</td>
            <td>{money(row['amount'])}</td>
            <td><span class="status-chip {status_cls}">{tr(lang, status.title(), status_ar.get(status, status))}</span></td>
            <td><a class="btn blue" href="{route_base(voucher_type)}/{row['id']}">{tr(lang, 'Open', 'فتح')}</a></td>
        </tr>
        """
    if not body:
        body = f"<tr><td colspan='7' style='text-align:center;'>{tr(lang, 'No vouchers found.', 'لا توجد سندات مسجلة.')}</td></tr>"
    html = f"""
    <div class="card">
        <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;">
            <h2>{voucher_list_title(lang, voucher_type)}</h2>
            <a class="btn green" href="{route_base(voucher_type)}/new">+ {tr(lang, 'New Voucher', 'سند جديد')}</a>
        </div>
    </div>
    <div class="card">
        <table>
            <tr>
                <th>{tr(lang, 'No', 'الرقم')}</th>
                <th>{tr(lang, 'Date', 'التاريخ')}</th>
                <th>{party_label(lang, voucher_type)}</th>
                <th>{tr(lang, 'Party Type', 'نوع الطرف')}</th>
                <th>{tr(lang, 'Amount', 'المبلغ')}</th>
                <th>{tr(lang, 'Status', 'الحالة')}</th>
                <th>{tr(lang, 'Action', 'الإجراء')}</th>
            </tr>
            {body}
        </table>
    </div>
    """
    return HTMLResponse(render_page(voucher_list_title(lang, voucher_type), html, lang, current_path=request.url.path))


@router.get("/ui/accounting/cash-receipts", response_class=HTMLResponse)
def cash_receipts_list(request: Request):
    return list_page(request, "receipt")


@router.get("/ui/accounting/cash-payments", response_class=HTMLResponse)
def cash_payments_list(request: Request):
    return list_page(request, "payment")


@router.get("/ui/accounting/cash-receipts/new", response_class=HTMLResponse)
def cash_receipts_new(request: Request):
    if not accounting_allowed(request, "create"):
        return HTMLResponse("Permission denied", status_code=403)
    lang = get_lang(request)
    params = request.query_params
    values = {
        "party_type": params.get("party_type"),
        "party_id": params.get("employee_id") or params.get("customer_id") or params.get("vendor_id"),
        "employee_trans_type": params.get("employee_trans_type"),
        "advance_id": params.get("advance_id"),
        "custody_request_id": params.get("custody_request_id"),
        "amount": params.get("amount"),
    }
    return HTMLResponse(render_page(voucher_title(lang, "receipt"), render_form(lang, "receipt", request.url.path, values), lang, current_path=request.url.path))


@router.get("/ui/accounting/cash-payments/new", response_class=HTMLResponse)
def cash_payments_new(request: Request):
    if not accounting_allowed(request, "create"):
        return HTMLResponse("Permission denied", status_code=403)
    lang = get_lang(request)
    params = request.query_params
    values = {
        "party_type": params.get("party_type"),
        "party_id": params.get("employee_id") or params.get("customer_id") or params.get("vendor_id"),
        "employee_trans_type": params.get("employee_trans_type"),
        "advance_id": params.get("advance_id"),
        "custody_request_id": params.get("custody_request_id"),
        "amount": params.get("amount"),
    }
    return HTMLResponse(render_page(voucher_title(lang, "payment"), render_form(lang, "payment", request.url.path, values), lang, current_path=request.url.path))


def normalize_party_data(
    conn,
    voucher_type: str,
    party_type: str,
    party_name: str,
    customer_id: str,
    vendor_id: str,
    employee_id: str,
    employee_trans_type: str,
    counter_account_code: str,
):
    party_type = safe(party_type).lower() or "other"
    party_id = 0
    partner = None

    if party_type == "customer":
        party_id = safe_int(customer_id)
        partner = get_partner(conn, "customer", party_id)
        if not partner:
            raise Exception("Customer is required")
        party_name = safe(partner["name"])
        counter_account_code = default_counter_account_for_party("customer", partner)
        if voucher_type != "receipt":
            raise Exception("Customer-linked cash vouchers should be created as cash receipts")

    elif party_type == "vendor":
        party_id = safe_int(vendor_id)
        partner = get_partner(conn, "vendor", party_id)
        if not partner:
            raise Exception("Vendor is required")
        party_name = safe(partner["name"])
        counter_account_code = default_counter_account_for_party("vendor", partner)
        if voucher_type != "payment":
            raise Exception("Vendor-linked cash vouchers should be created as cash payments")

    elif party_type == "employee":
        party_id = safe_int(employee_id)
        emp = conn.execute("SELECT name FROM employees WHERE id = ?", (party_id,)).fetchone()
        if not emp:
            raise Exception("Employee is required")
        party_name = safe(emp["name"])
        trans_type = safe(employee_trans_type).lower() or "advance"
        if trans_type not in ("advance", "custody"):
            raise Exception("Please select employee transaction type (Advance/Custody).")
        if trans_type == "custody":
            counter_account_code = safe(get_setting_value("employee_custody_account", "112200"))
            if not counter_account_code:
                raise Exception("Please set Employee Custody Account in configuration.")
        else:
            counter_account_code = safe(get_setting_value("employee_advance_account", "121200"))
            if not counter_account_code:
                raise Exception("Please set Employee Advance Account in configuration.")

    return party_type, party_id, safe(party_name), safe(counter_account_code)


def save_voucher(
    request: Request,
    voucher_type: str,
    voucher_no: str,
    voucher_date: str,
    party_name: str,
    party_type: str,
    customer_id: str,
    vendor_id: str,
    employee_id: str,
    employee_trans_type: str,
    advance_id: str,
    custody_request_id: str,
    liquidity_account_code: str,
    counter_account_code: str,
    amount: str,
    description: str,
    signature_name: str,
):
    if not accounting_allowed(request, "create"):
        return HTMLResponse("Permission denied", status_code=403)
    lang = get_lang(request)
    values = {
        "voucher_no": voucher_no,
        "voucher_date": voucher_date,
        "party_name": party_name,
        "party_type": party_type,
        "party_id": customer_id if safe(party_type).lower() == "customer" else (vendor_id if safe(party_type).lower() == "vendor" else employee_id),
        "employee_trans_type": employee_trans_type,
        "advance_id": advance_id,
        "custody_request_id": custody_request_id,
        "liquidity_account_code": liquidity_account_code,
        "counter_account_code": counter_account_code,
        "amount": amount,
        "description": description,
        "signature_name": signature_name,
    }
    conn = None
    try:
        conn = get_conn()
        party_type, party_id, party_name, counter_account_code = normalize_party_data(
            conn,
            voucher_type,
            party_type,
            party_name,
            customer_id,
            vendor_id,
            employee_id,
            employee_trans_type,
            counter_account_code,
        )
        selected_advance_id = None
        selected_custody_request_id = None

        # For employee disbursements, amount must come from the selected request
        # (advance or custody request), not manual input.
        if party_type == "employee":
            trans_type = safe(employee_trans_type).lower()
            if trans_type == "advance":
                selected_advance_id = safe_int(advance_id)
                if selected_advance_id <= 0:
                    raise Exception("Please select an advance request.")
                advance_row = conn.execute(
                    """
                    SELECT id, amount
                    FROM employee_advances
                    WHERE id = ?
                      AND employee_id = ?
                      AND LOWER(COALESCE(status, 'active')) = 'active'
                    LIMIT 1
                    """,
                    (selected_advance_id, party_id),
                ).fetchone()
                if not advance_row:
                    raise Exception("Selected advance request is not pending for this employee.")
                amount = str(float(advance_row["amount"] or 0))
            elif trans_type == "custody":
                selected_custody_request_id = safe_int(custody_request_id)
                if selected_custody_request_id <= 0:
                    raise Exception("Please select a custody request.")
                custody_row = conn.execute(
                    """
                    SELECT id, amount
                    FROM employee_custody_requests
                    WHERE id = ?
                      AND employee_id = ?
                      AND LOWER(COALESCE(status, 'active')) = 'active'
                      AND NOT EXISTS (
                          SELECT 1
                          FROM cash_vouchers v
                          WHERE COALESCE(v.custody_request_id, 0) = employee_custody_requests.id
                            AND LOWER(COALESCE(v.voucher_type,'')) = 'payment'
                            AND LOWER(COALESCE(v.employee_trans_type,'')) = 'custody'
                            AND LOWER(COALESCE(v.status,'')) <> 'reversed'
                      )
                    LIMIT 1
                    """,
                    (selected_custody_request_id, party_id),
                ).fetchone()
                if not custody_row:
                    raise Exception("Selected custody request is not pending for this employee.")
                amount = str(float(custody_row["amount"] or 0))

        validate_voucher(voucher_date, party_name, party_type, party_id, liquidity_account_code, counter_account_code, amount)
        cur = conn.execute(
            """
            INSERT INTO cash_vouchers (
                voucher_type, voucher_no, voucher_date, party_name, party_type, party_id,
                liquidity_account_code, counter_account_code, amount, description, signature_name, 
                employee_trans_type, advance_id, custody_request_id, status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft')
            """,
            (
                voucher_type,
                safe(voucher_no) or next_voucher_no(voucher_type),
                safe(voucher_date),
                party_name,
                party_type,
                party_id if party_id > 0 else None,
                safe(liquidity_account_code),
                counter_account_code,
                float(q2(amount)),
                safe(description),
                safe(signature_name),
                employee_trans_type if party_type == "employee" else None,
                selected_advance_id if party_type == "employee" and safe(employee_trans_type).lower() == "advance" else None,
                selected_custody_request_id if party_type == "employee" and safe(employee_trans_type).lower() == "custody" else None,
            ),
        )
        voucher_id = cur.lastrowid
        create_draft_journal(conn, voucher_id)
        conn.commit()
        conn.close()
        return RedirectResponse(f"{route_base(voucher_type)}/{voucher_id}", status_code=302)
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        return HTMLResponse(
            render_page(voucher_title(lang, voucher_type), render_form(lang, voucher_type, request.url.path, values, str(e)), lang, current_path=request.url.path),
            status_code=400,
        )


@router.post("/ui/accounting/cash-receipts/new")
def create_cash_receipt(
    request: Request,
    voucher_no: str = Form(""),
    voucher_date: str = Form(""),
    party_name: str = Form(""),
    party_type: str = Form(""),
    customer_id: str = Form(""),
    vendor_id: str = Form(""),
    employee_id: str = Form(""),
    employee_trans_type: str = Form(""),
    advance_id: str = Form(""),
    custody_request_id: str = Form(""),
    liquidity_account_code: str = Form(""),
    counter_account_code: str = Form(""),
    amount: str = Form("0"),
    description: str = Form(""),
    signature_name: str = Form(""),
):
    return save_voucher(request, "receipt", voucher_no, voucher_date, party_name, party_type, customer_id, vendor_id, employee_id, employee_trans_type, advance_id, custody_request_id, liquidity_account_code, counter_account_code, amount, description, signature_name)


@router.post("/ui/accounting/cash-payments/new")
def create_cash_payment(
    request: Request,
    voucher_no: str = Form(""),
    voucher_date: str = Form(""),
    party_name: str = Form(""),
    party_type: str = Form(""),
    customer_id: str = Form(""),
    vendor_id: str = Form(""),
    employee_id: str = Form(""),
    employee_trans_type: str = Form(""),
    advance_id: str = Form(""),
    custody_request_id: str = Form(""),
    liquidity_account_code: str = Form(""),
    counter_account_code: str = Form(""),
    amount: str = Form("0"),
    description: str = Form(""),
    signature_name: str = Form(""),
):
    return save_voucher(request, "payment", voucher_no, voucher_date, party_name, party_type, customer_id, vendor_id, employee_id, employee_trans_type, advance_id, custody_request_id, liquidity_account_code, counter_account_code, amount, description, signature_name)


def render_allocation_card(lang: str, conn, voucher):
    payment_type = voucher_payment_type(voucher)
    if not payment_type:
        return ""

    total_allocated = get_allocated_total_for_payment(conn, payment_type, voucher["id"])
    unallocated = get_payment_unallocated_amount(conn, payment_type, voucher["id"])
    rows = allocation_rows_for_voucher(conn, voucher)

    body = ""
    for row in rows:
        body += f"""
        <tr>
            <td>{safe(row['doc_no'])}</td>
            <td>{safe(row['doc_date'])}</td>
            <td>{money(row['doc_total'])}</td>
            <td>{money(row['allocated_amount'])}</td>
            <td><a class="btn blue" href="{safe(row['open_url'])}">{tr(lang, 'Open', 'فتح')}</a></td>
        </tr>
        """
    if not body:
        body = f"<tr><td colspan='5' style='text-align:center;'>{tr(lang, 'No allocations yet.', 'لا توجد تسويات بعد.')}</td></tr>"

    label = tr(lang, "Available for allocation", "المتاح للتسوية")
    return f"""
    <div class="card" style="margin-top:18px;">
        <div style="display:flex;gap:12px;flex-wrap:wrap;align-items:center;margin-bottom:10px;">
            <span class="chip">{tr(lang, 'Allocated', 'المخصص')}: {money(total_allocated)}</span>
            <span class="chip">{label}: {money(unallocated)}</span>
        </div>
        <table>
            <tr>
                <th>{tr(lang, 'Document No', 'رقم المستند')}</th>
                <th>{tr(lang, 'Date', 'التاريخ')}</th>
                <th>{tr(lang, 'Document Total', 'إجمالي المستند')}</th>
                <th>{tr(lang, 'Allocated', 'المخصص')}</th>
                <th>{tr(lang, 'Action', 'الإجراء')}</th>
            </tr>
            {body}
        </table>
    </div>
    """


def open_voucher_page(request: Request, voucher_id: int, voucher_type: str):
    if not accounting_allowed(request, "view"):
        return HTMLResponse("Permission denied", status_code=403)
    lang = get_lang(request)
    conn = get_conn()
    voucher = get_voucher(conn, voucher_id)
    if not voucher or safe(voucher["voucher_type"]) != voucher_type:
        conn.close()
        return HTMLResponse(tr(lang, "Voucher not found", "السند غير موجود"), status_code=404)

    status = safe(voucher["status"]).lower()
    status_cls = "green" if status == "posted" else ("red" if status == "reversed" else "orange")
    status_ar = {"draft": "مسودة", "posted": "مرحل", "reversed": "معكوس"}

    post_btn = ""
    if status == "draft" and accounting_allowed(request, "post"):
        post_btn = f"<form method='post' action='{route_base(voucher_type)}/{voucher_id}/post' style='display:inline;'><button class='btn green' type='submit'>{tr(lang, 'Post', 'ترحيل')}</button></form>"

    allocation_html = render_allocation_card(lang, conn, voucher) if status == "posted" else ""
    conn.close()

    html = f"""
    <div class="card">
        <h2>{voucher_title(lang, voucher_type)} {safe(voucher['voucher_no'])}</h2>
        <p><b>{tr(lang, 'Date:', 'التاريخ:')}</b> {safe(voucher['voucher_date'])}</p>
        <p><b>{party_label(lang, voucher_type)}:</b> {safe(voucher['party_name'])}</p>
        <p><b>{tr(lang, 'Party Type:', 'نوع الطرف:')}</b> {safe(voucher['party_type']).title()}</p>
        <p><b>{tr(lang, 'Cash / Bank Account:', 'حساب النقدية / البنك:')}</b> {account_display(voucher['liquidity_account_code'])}</p>
        <p><b>{tr(lang, 'Counter Account:', 'الحساب المقابل:')}</b> {account_display(voucher['counter_account_code'])}</p>
        <p><b>{tr(lang, 'Amount:', 'المبلغ:')}</b> {money(voucher['amount'])}</p>
        <p><b>{tr(lang, 'Description:', 'البيان:')}</b> {safe(voucher['description'])}</p>
        <p><b>{signature_label(lang, voucher_type)}:</b> {safe(voucher['signature_name'])}</p>
        <p><b>{tr(lang, 'Status:', 'الحالة:')}</b> <span class="status-chip {status_cls}">{tr(lang, status.title(), status_ar.get(status, status))}</span></p>
        <p><b>{tr(lang, 'Journal ID:', 'رقم القيد:')}</b> {safe(voucher['journal_id'])}</p>
        <p><b>{tr(lang, 'Reverse Journal ID:', 'رقم قيد العكس:')}</b> {safe(voucher['reversed_journal_id'])}</p>
        <div style="margin-top:18px;display:flex;gap:8px;flex-wrap:wrap;">
            <a class="btn blue" href="{route_base(voucher_type)}/{voucher_id}/print" target="_blank">{tr(lang, 'Print', 'طباعة')}</a>
            {post_btn}
            <a class="btn gray" href="{route_base(voucher_type)}">{tr(lang, 'Back', 'رجوع')}</a>
        </div>
    </div>
    {allocation_html}
    """
    return HTMLResponse(render_page(voucher_title(lang, voucher_type), html, lang, current_path=request.url.path))


@router.get("/ui/accounting/cash-receipts/{voucher_id}", response_class=HTMLResponse)
def open_cash_receipt(request: Request, voucher_id: int):
    return open_voucher_page(request, voucher_id, "receipt")


@router.get("/ui/accounting/cash-payments/{voucher_id}", response_class=HTMLResponse)
def open_cash_payment(request: Request, voucher_id: int):
    return open_voucher_page(request, voucher_id, "payment")


def allocated_documents_for_voucher(conn, voucher):
    payment_type = voucher_payment_type(voucher)
    if not payment_type:
        return []
    return [dict(row) for row in get_payment_allocations(conn, payment_type, voucher["id"])]


def refresh_documents_after_allocation_delete(conn, allocated_rows):
    for row in allocated_rows:
        if safe(row["document_type"]) == "customer_invoice":
            refresh_customer_invoice_payment_status(conn, row["document_id"])
        elif safe(row["document_type"]) == "vendor_bill":
            refresh_vendor_bill_payment_status(conn, row["document_id"])


def set_voucher_status(request: Request, voucher_id: int, voucher_type: str, action: str):
    if not accounting_allowed(request, "post"):
        return HTMLResponse("Permission denied", status_code=403)
    conn = get_conn()
    voucher = get_voucher(conn, voucher_id)
    if not voucher or safe(voucher["voucher_type"]) != voucher_type:
        conn.close()
        return HTMLResponse("Voucher not found", status_code=404)
    try:
        if action == "post":
            if safe(voucher["status"]).lower() != "draft":
                raise Exception("Only draft vouchers can be posted")
            submit_journal_for_final_post(conn, voucher["journal_id"])
            conn.execute("UPDATE cash_vouchers SET status = 'posted' WHERE id = ?", (voucher_id,))
            
            # Update employee advance status if linked
            if safe(voucher["party_type"]).lower() == "employee" and safe(voucher["employee_trans_type"]).lower() == "advance" and voucher["advance_id"]:
                conn.execute("UPDATE employee_advances SET status = 'open' WHERE id = ?", (voucher["advance_id"],))
            if safe(voucher["party_type"]).lower() == "employee" and safe(voucher["employee_trans_type"]).lower() == "custody" and safe_int(voucher["custody_request_id"]) > 0:
                conn.execute("UPDATE employee_custody_requests SET status = 'open' WHERE id = ?", (voucher["custody_request_id"],))
        else:
            if safe(voucher["status"]).lower() != "posted":
                raise Exception("Only posted vouchers can be reversed")
            allocated_rows = allocated_documents_for_voucher(conn, voucher)
            payment_type = voucher_payment_type(voucher)
            if payment_type:
                delete_payment_allocations(conn, payment_type, voucher["id"])
            refresh_documents_after_allocation_delete(conn, allocated_rows)
            reverse_id = reverse_journal_entry(conn, voucher["journal_id"])
            conn.execute("UPDATE cash_vouchers SET status = 'reversed', reversed_journal_id = ? WHERE id = ?", (reverse_id, voucher_id))
            
            # Revert employee advance status if linked
            if safe(voucher["party_type"]).lower() == "employee" and safe(voucher["employee_trans_type"]).lower() == "advance" and voucher["advance_id"]:
                conn.execute("UPDATE employee_advances SET status = 'active' WHERE id = ?", (voucher["advance_id"],))
            if safe(voucher["party_type"]).lower() == "employee" and safe(voucher["employee_trans_type"]).lower() == "custody" and safe_int(voucher["custody_request_id"]) > 0:
                conn.execute("UPDATE employee_custody_requests SET status = 'active' WHERE id = ?", (voucher["custody_request_id"],))
        conn.commit()
    except Exception as e:
        conn.rollback()
        conn.close()
        return HTMLResponse(str(e), status_code=400)
    conn.close()
    return RedirectResponse(f"{route_base(voucher_type)}/{voucher_id}", status_code=302)


@router.post("/ui/accounting/cash-receipts/{voucher_id}/post")
def post_cash_receipt(request: Request, voucher_id: int):
    return set_voucher_status(request, voucher_id, "receipt", "post")


@router.post("/ui/accounting/cash-payments/{voucher_id}/post")
def post_cash_payment(request: Request, voucher_id: int):
    return set_voucher_status(request, voucher_id, "payment", "post")


@router.post("/ui/accounting/cash-receipts/{voucher_id}/reverse")
def reverse_cash_receipt(request: Request, voucher_id: int):
    return set_voucher_status(request, voucher_id, "receipt", "reverse")


@router.post("/ui/accounting/cash-payments/{voucher_id}/reverse")
def reverse_cash_payment(request: Request, voucher_id: int):
    return set_voucher_status(request, voucher_id, "payment", "reverse")


def print_voucher_page(request: Request, voucher_id: int, voucher_type: str):
    if not accounting_allowed(request, "view"):
        return HTMLResponse("Permission denied", status_code=403)
    lang = get_lang(request)
    conn = get_conn()
    voucher = get_voucher(conn, voucher_id)
    conn.close()
    if not voucher or safe(voucher["voucher_type"]) != voucher_type:
        return HTMLResponse(tr(lang, "Voucher not found", "السند غير موجود"), status_code=404)
    html = f"""
    <!DOCTYPE html>
    <html lang="{lang}" dir="{'rtl' if lang == 'ar' else 'ltr'}">
    <head>
        <meta charset="UTF-8">
        <title>{voucher_title(lang, voucher_type)}</title>
        <style>
            body {{ font-family: Arial, sans-serif; color: #17355c; padding: 24px; }}
            .sheet {{ max-width: 900px; margin: 0 auto; border: 1px solid #dfe6f1; border-radius: 16px; padding: 28px; }}
            .grid {{ display:grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 14px; }}
            .box {{ border:1px solid #dfe6f1; border-radius: 12px; padding: 12px 14px; min-height: 74px; }}
            .label {{ font-size:12px; color:#678; margin-bottom:6px; }}
            .value {{ font-size:18px; font-weight:700; }}
            .wide {{ grid-column:1 / -1; }}
            .signatures {{ display:grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap:24px; margin-top:48px; }}
            .sig-line {{ border-top:1px solid #1e3556; margin-top:54px; padding-top:8px; text-align:center; }}
            .print-bar {{ margin-bottom:16px; }}
            @media print {{ .print-bar {{ display:none; }} body {{ padding:0; }} .sheet {{ border:none; }} }}
        </style>
    </head>
    <body>
        <div class="print-bar"><button onclick="window.print()">{tr(lang, 'Print', 'طباعة')}</button></div>
        <div class="sheet">
            <h1>{voucher_title(lang, voucher_type)}</h1>
            <div class="grid">
                <div class="box"><div class="label">{tr(lang, 'Voucher No', 'رقم السند')}</div><div class="value">{safe(voucher['voucher_no'])}</div></div>
                <div class="box"><div class="label">{tr(lang, 'Date', 'التاريخ')}</div><div class="value">{safe(voucher['voucher_date'])}</div></div>
                <div class="box"><div class="label">{party_label(lang, voucher_type)}</div><div class="value">{safe(voucher['party_name'])}</div></div>
                <div class="box"><div class="label">{tr(lang, 'Party Type', 'نوع الطرف')}</div><div class="value">{safe(voucher['party_type']).title()}</div></div>
                <div class="box"><div class="label">{tr(lang, 'Cash / Bank Account', 'حساب النقدية / البنك')}</div><div class="value">{account_display(voucher['liquidity_account_code'])}</div></div>
                <div class="box"><div class="label">{tr(lang, 'Counter Account', 'الحساب المقابل')}</div><div class="value">{account_display(voucher['counter_account_code'])}</div></div>
                <div class="box"><div class="label">{tr(lang, 'Amount', 'المبلغ')}</div><div class="value">{money(voucher['amount'])}</div></div>
                <div class="box"><div class="label">{signature_label(lang, voucher_type)}</div><div class="value">{safe(voucher['signature_name'])}</div></div>
                <div class="box wide"><div class="label">{tr(lang, 'Description', 'البيان')}</div><div class="value">{safe(voucher['description'])}</div></div>
                <div class="box wide"><div class="label">{tr(lang, 'Amount in Words', 'المبلغ كتابة')}</div><div class="value">{amount_in_words(voucher['amount'])}</div></div>
            </div>
            <div class="signatures">
                <div class="sig-line">{tr(lang, 'Prepared By', 'المحاسب')}</div>
                <div class="sig-line">{signature_label(lang, voucher_type)}</div>
                <div class="sig-line">{tr(lang, 'Approved By', 'الاعتماد')}</div>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(html)


@router.get("/ui/accounting/cash-receipts/{voucher_id}/print", response_class=HTMLResponse)
def print_cash_receipt(request: Request, voucher_id: int):
    return print_voucher_page(request, voucher_id, "receipt")


@router.get("/ui/accounting/cash-payments/{voucher_id}/print", response_class=HTMLResponse)
def print_cash_payment(request: Request, voucher_id: int):
    return print_voucher_page(request, voucher_id, "payment")


