import json
import os
from base64 import b64decode

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from itsdangerous import BadSignature, TimestampSigner
from starlette.middleware.sessions import SessionMiddleware

from auth import can, default_home_path_for_user, is_logged_in
from db import init_db
from i18n import get_lang
from layout import render_page

init_db()

app = FastAPI(title="Premium One ERP")
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SESSION_SECRET", "premium-one-erp-session-key"),
    same_site="lax",
    https_only=bool(os.environ.get("RENDER") or os.environ.get("RENDER_EXTERNAL_URL")),
)
app.mount("/static", StaticFiles(directory="static"), name="static")
session_signer = TimestampSigner("premium-one-erp-session-key")


def module_for_path(path: str):
    path = path or ""
    rules = [
        ("/ui/settings", "system"),
        ("/ui/system/users", "users"),
        ("/ui/accounting/fixed-assets", "fixed_assets"),
        ("/ui/accounting/reports", "reports"),
        ("/ui/accounting/general-ledger", "reports"),
        ("/ui/accounting/trial-balance", "reports"),
        ("/ui/accounting/profit-loss", "reports"),
        ("/ui/accounting/balance-sheet", "reports"),
        ("/ui/accounting/partner-ledger", "reports"),
        ("/ui/accounting/aging", "reports"),
        ("/ui/accounting/monthly-dues", "reports"),
        ("/ui/accounting/petty-cash/statement", "reports"),
        ("/ui/hr", "hr"),
        ("/ui/inventory", "inventory"),
        ("/ui/purchasing", "purchasing"),
        ("/ui/sales", "sales"),
        ("/ui/operations", "operations"),
        ("/ui/projects", "operations"),
        ("/ui/accounting", "accounting"),
    ]
    for prefix, module_code in rules:
        if path.startswith(prefix):
            return module_code
    return None


def hydrate_session_from_cookie(request: Request):
    if request.scope.get("session"):
        return

    raw_cookie = request.cookies.get("session")
    if not raw_cookie:
        request.scope["session"] = {}
        return

    try:
        data = session_signer.unsign(raw_cookie.encode("utf-8"), max_age=14 * 24 * 60 * 60)
        request.scope["session"] = json.loads(b64decode(data))
    except (BadSignature, ValueError, TypeError):
        request.scope["session"] = {}


def _is_session_logged_in(request: Request) -> bool:
    """Stable login check for Render and local runs."""
    try:
        if request.session.get("logged_in"):
            return True
        if request.session.get("user_id"):
            return True
        if request.session.get("user"):
            return True
        return bool(is_logged_in(request))
    except Exception:
        return False


@app.middleware("http")
async def auth_guard(request: Request, call_next):
    path = request.url.path or ""

    open_paths = [
        "/login",
        "/logout",
        "/static",
        "/favicon.ico",
        "/test",
        "/docs",
        "/openapi.json",
        "/redoc",
    ]

    if path.startswith("/api"):
        return await call_next(request)

    if any(path.startswith(prefix) for prefix in open_paths):
        return await call_next(request)

    if not _is_session_logged_in(request):
        return RedirectResponse("/login", status_code=302)

    return await call_next(request)


def dashboard_cards(cards):
    html = '<div class="card-grid">'
    for title, href, icon, desc in cards:
        icon_html = f'<img src="{icon}" alt="{title} icon">' if icon.startswith("/static/") else icon
        html += f"""
        <a href="{href}" class="module-card">
            <div class="module-card-icon">{icon_html}</div>
            <div class="module-card-title">{title}</div>
            <div class="module-card-sub">{desc}</div>
        </a>
        """
    html += "</div>"
    return html


def card_section(title, cards):
    return f"""
    <div class="card">
        <h3 class="sub-title">{title}</h3>
        {dashboard_cards(cards)}
    </div>
    """


def t(lang: str, en: str, ar: str) -> str:
    return ar if lang == "ar" else en


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    error = request.query_params.get("error")
    error_html = "<div class='error'>Invalid login. Please try again.</div>" if error else ""
    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Login - Premium One ERP</title>
        <link rel="manifest" href="/static/manifest.json">
        <meta name="theme-color" content="#052861">
        <style>
            * {{ box-sizing: border-box; font-family: Arial, sans-serif; }}
            body {{
                margin: 0;
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
                background:
                    radial-gradient(circle at 22% 20%, rgba(32, 211, 243, 0.22), transparent 26%),
                    linear-gradient(135deg, #052861 0%, #0a3a8f 55%, #041f4d 100%);
            }}
            .login-card {{
                width: 100%; max-width: 420px; background: rgba(255,255,255,0.98);
                border-radius: 22px; padding: 28px; box-shadow: 0 24px 60px rgba(0,0,0,0.25);
                border: 1px solid rgba(255,255,255,0.22);
            }}
            .logo {{ text-align:center; margin-bottom: 18px; }}
            .logo img {{ width: 210px; max-width: 100%; height: auto; filter: drop-shadow(0 8px 18px rgba(0,0,0,0.18)); }}
            h1 {{ margin: 0 0 8px 0; color: #13315c; font-size: 24px; text-align:center; }}
            p {{ margin: 0 0 22px 0; color: #6d809c; text-align:center; }}
            label {{ display:block; margin-bottom: 7px; color:#3a567d; font-weight:700; font-size:13px; }}
            input {{ width:100%; padding: 13px 14px; border:1px solid #d5deea; border-radius: 12px; outline:none; font-size:14px; margin-bottom:14px; }}
            button {{ width:100%; padding: 13px 16px; border:0; border-radius: 12px; background: linear-gradient(135deg, #174cb7 0%, #1d67e2 58%, #1dbbe8 100%); color:white; font-weight:800; cursor:pointer; font-size:15px; box-shadow: 0 12px 22px rgba(14,79,184,0.24); }}
            .hint {{ margin-top:14px; font-size:12px; color:#6d809c; text-align:center; }}
            .error {{ background:#fdecec; color:#b42318; border:1px solid #f6c7c4; padding:10px 12px; border-radius:12px; margin-bottom:14px; font-weight:700; }}
        </style>
    </head>
    <body>
        <form class="login-card" method="post" action="/login">
            <div class="logo"><img src="/static/logo6.png" alt="Premium One ERP"></div>
            <h1>Premium One ERP</h1>
            <p>Sign in to continue</p>
            {error_html}
            <label>Username</label>
            <input name="username" placeholder="Enter username" autocomplete="username" required>
            <label>Password</label>
            <input name="password" type="password" placeholder="Enter password" autocomplete="current-password" required>
            <button type="submit">Login</button>
            <div class="hint">Temporary Render login: any username/password works.</div>
        </form>
    </body>
    </html>
    """)


@app.post("/login")
async def login_submit(request: Request):
    form = await request.form()
    username = str(form.get("username") or "").strip()
    password = str(form.get("password") or "").strip()

    if not username or not password:
        return RedirectResponse("/login?error=1", status_code=303)

    request.session.clear()
    request.session["logged_in"] = True
    request.session["user_id"] = 1
    request.session["username"] = username
    request.session["role"] = "admin"
    request.session["is_admin"] = True
    request.session["user"] = {"id": 1, "username": username, "name": username, "role": "admin", "is_admin": True}
    return RedirectResponse("/ui/accounting", status_code=303)


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=302)


@app.get("/test", response_class=HTMLResponse)
def test():
    return "<h2>System Running 🚀</h2>"


@app.get("/")
def root(request: Request):
    if _is_session_logged_in(request):
        return RedirectResponse("/ui/accounting", status_code=302)
    return RedirectResponse("/login", status_code=302)


@app.get("/ui")
def ui_root(request: Request):
    if _is_session_logged_in(request):
        return RedirectResponse("/ui/accounting", status_code=302)
    return RedirectResponse("/login", status_code=302)


@app.get("/ui/settings", response_class=HTMLResponse)
def settings_root(request: Request):
    lang = get_lang(request)
    settings_cards = [
        (
            t(lang, "Company Profile", "بيانات الشركة"),
            "/ui/accounting/setup",
            "/static/icons/system-setup.svg",
            t(lang, "Company data, logo, base currency, and feature activation.", "بيانات الشركة والشعار والعملة الأساسية وتفعيل الخصائص."),
        ),
        (
            t(lang, "Accounting Configuration", "الإعدادات المحاسبية"),
            "/ui/accounting/config",
            "/static/icons/configuration.svg",
            t(lang, "Default accounts, prefixes, and accounting defaults.", "الحسابات الافتراضية والبادئات والإعدادات المحاسبية الأساسية."),
        ),
        (
            t(lang, "Users & Permissions", "المستخدمون والصلاحيات"),
            "/ui/system/users",
            "/static/icons/employees.svg",
            t(lang, "Create users, assign roles, and control access levels.", "إنشاء المستخدمين وتحديد الأدوار والتحكم في مستويات الصلاحية."),
        ),
    ]

    content = f"""
    <div class="card">
        <h2>{t(lang, "Settings", "الإعدادات")}</h2>
        <p style="color:#6d809c; margin-top:8px;">
            {t(lang, "General system settings in one place without mixing them with daily transactions.", "كل الإعدادات العامة في مكان واحد بدون خلطها مع الحركات اليومية.")}
        </p>
    </div>
    {card_section(t(lang, "System Settings", "إعدادات النظام"), settings_cards)}
    """
    return HTMLResponse(render_page(t(lang, "Settings", "الإعدادات"), content, lang, current_path="/ui/settings"))


@app.get("/ui/accounting", response_class=HTMLResponse)
def accounting_root(request: Request):
    lang = get_lang(request)
    main_cards = [
        (t(lang, "System Setup", "تهيئة النظام"), "/ui/accounting/setup", "/static/icons/system-setup.svg", t(lang, "Company and system initialization", "تهيئة بيانات الشركة والنظام")),
        (t(lang, "Configuration", "الإعدادات"), "/ui/accounting/config", "/static/icons/configuration.svg", t(lang, "Default accounts and prefixes", "الحسابات الافتراضية والبدايات")),
        (t(lang, "Chart of Accounts", "دليل الحسابات"), "/ui/accounting/accounts", "/static/icons/chart-accounts.svg", t(lang, "Manage account structure", "إدارة هيكل الحسابات")),
        (t(lang, "Cost Centers", "مراكز التكلفة"), "/ui/accounting/cost-centers", "/static/icons/cost-centers.svg", t(lang, "Department and activity allocation", "توزيع الأقسام والأنشطة")),
        (t(lang, "Customers", "العملاء"), "/ui/accounting/customers-hub", "/static/icons/customers.svg", t(lang, "Customer master and transactions", "بيانات العملاء وحركاتهم")),
        (t(lang, "Vendors", "الموردون"), "/ui/accounting/vendors-hub", "/static/icons/vendors.svg", t(lang, "Vendor master and transactions", "بيانات الموردين وحركاتهم")),
        (t(lang, "Journal", "اليومية"), "/ui/accounting/journal", "/static/icons/journal.svg", t(lang, "Journal entries and review", "قيود اليومية والمراجعة")),
        (t(lang, "Expenses", "المصروفات"), "/ui/accounting/expenses", "/static/icons/expenses.svg", t(lang, "Operational expenses and posting", "المصروفات التشغيلية وترحيلها")),
        (t(lang, "Cash Receipts", "سندات القبض"), "/ui/accounting/cash-receipts", "/static/icons/customer-payments.svg", t(lang, "Cash receipt vouchers with posting and print.", "سندات قبض نقدي مع الترحيل والطباعة.")),
        (t(lang, "Cash Payments", "سندات الصرف"), "/ui/accounting/cash-payments", "/static/icons/vendor-payments.svg", t(lang, "Cash payment vouchers with posting and print.", "سندات صرف نقدي مع الترحيل والطباعة.")),
        (t(lang, "Employee Advances", "سلف الموظفين"), "/ui/accounting/employee-advances", "/static/icons/reports.svg", t(lang, "Disbursement, balances, and payroll deduction tracking", "صرف السلف، الأرصدة، ومتابعة خصم المرتبات")),
        (t(lang, "Petty Cash", "العهدة النقدية"), "/ui/accounting/petty-cash", "/static/icons/petty-cash.svg", t(lang, "Custody and returns", "العهدة والردود")),
        (t(lang, "Fixed Assets", "الأصول الثابتة"), "/ui/accounting/fixed-assets", "/static/icons/fixed-assets.svg", t(lang, "Assets, depreciation, and disposal", "الأصول والإهلاك والاستبعاد")),
        (t(lang, "Reports", "التقارير"), "/ui/accounting/reports", "/static/icons/reports.svg", t(lang, "Financial and operational reports", "التقارير المالية والتشغيلية")),
    ]
    content = card_section(t(lang, "Accounting", "الحسابات"), main_cards)
    return HTMLResponse(render_page(t(lang, "Accounting", "الحسابات"), content, lang, current_path="/ui/accounting"))


@app.get("/ui/accounting/customers-hub", response_class=HTMLResponse)
def customers_hub():
    cards = [
        ("Customers", "/ui/accounting/customers", "/static/icons/customers.svg", "Customer master data"),
        ("Customer Invoices", "/ui/accounting/customer-invoices", "/static/icons/customer-invoices.svg", "Sales invoices"),
        ("Customer Statement", "/ui/accounting/customer-statement", "/static/icons/customer-statement.svg", "Account statement and balances"),
    ]
    content = card_section("Customers", cards)
    return HTMLResponse(render_page("Customers", content, current_path="/ui/accounting/customers-hub"))


@app.get("/ui/accounting/vendors-hub", response_class=HTMLResponse)
def vendors_hub():
    cards = [
        ("Vendors", "/ui/accounting/vendors", "/static/icons/vendors.svg", "Vendor master data"),
        ("Vendor Bills", "/ui/accounting/vendor-bills", "/static/icons/vendor-bills.svg", "Purchase bills"),
        ("Vendor Statement", "/ui/accounting/vendor-statement", "/static/icons/vendor-statement.svg", "Account statement and balances"),
    ]
    content = card_section("Vendors", cards)
    return HTMLResponse(render_page("Vendors", content, current_path="/ui/accounting/vendors-hub"))


@app.get("/ui/hr", response_class=HTMLResponse)
def hr_root(request: Request):
    lang = get_lang(request)
    hr_cards = [
        (t(lang, "Employees", "الموظفون"), "/ui/hr/employees", "/static/icons/employees.svg", t(lang, "Employee master data and import template", "بيانات الموظفين وقالب الاستيراد")),
        (t(lang, "Employee Categories", "فئات الموظفين"), "/ui/hr/categories", "/static/icons/employees.svg", t(lang, "Attendance groups, roles, shifts, and grace rules", "مجموعات الحضور والأدوار والورديات وقواعد السماح")),
        (t(lang, "Attendance", "الحضور"), "/ui/hr/attendance", "/static/icons/reports.svg", t(lang, "Biometric attendance import and daily logs", "استيراد البصمة وسجلات الحضور اليومية")),
        (t(lang, "Payroll", "المرتبات"), "/ui/hr/payroll", "/static/icons/reports.svg", t(lang, "Monthly payroll generation, review, and posting", "إعداد مسير المرتبات الشهري ومراجعته وترحيله")),
    ]
    content = card_section(t(lang, "HR", "الموارد البشرية"), hr_cards)
    return HTMLResponse(render_page(t(lang, "HR", "الموارد البشرية"), content, lang, current_path="/ui/hr"))


@app.get("/ui/inventory", response_class=HTMLResponse)
def inventory_root():
    inventory_cards = [
        ("Items", "/ui/inventory/items", "/static/icons/items.svg", "Item master and stock products"),
        ("Warehouses", "/ui/inventory/warehouses", "/static/icons/warehouses.svg", "Warehouse structure and status"),
        ("Goods Receipts", "/ui/inventory/goods-receipts", "/static/icons/goods-receipts.svg", "Receiving and stock intake"),
        ("Stock Balance", "/ui/inventory/stock-balance", "/static/icons/stock-balance.svg", "Current stock by item and warehouse"),
        ("Stock Ledger", "/ui/inventory/stock-ledger", "/static/icons/stock-ledger.svg", "Detailed inventory movement history"),
    ]
    content = card_section("Inventory", inventory_cards)
    return HTMLResponse(render_page("Inventory", content, current_path="/ui/inventory"))


@app.get("/ui/purchasing", response_class=HTMLResponse)
def purchasing_root():
    purchasing_cards = [
        ("Purchase Orders", "/ui/purchasing/purchase-orders", "/static/icons/purchase-orders.svg", "Purchase orders and follow-up"),
        ("PO Variances", "/ui/purchasing/po-variances", "/static/icons/po-variances.svg", "Review quantity and price differences"),
    ]
    content = card_section("Purchasing", purchasing_cards)
    return HTMLResponse(render_page("Purchasing", content, current_path="/ui/purchasing"))


from modules.accounting.accounts import router as accounts_router
from modules.accounting.config import router as config_router
from modules.accounting.customer_invoices import router as customer_invoices_router
from modules.accounting.journal import router as journal_router
from modules.accounting.partners import router as partners_router
from modules.accounting.setup import router as setup_router
from modules.accounting.vendor_bills import router as vendor_bills_router

try:
    from modules.accounting.cash_vouchers import router as cash_vouchers_router
except Exception:
    cash_vouchers_router = None

try:
    from modules.accounting.customer_payments import router as customer_payments_router
except Exception:
    customer_payments_router = None

try:
    from modules.accounting.customer_statement import router as customer_statement_router
except Exception:
    customer_statement_router = None

try:
    from modules.accounting.fixed_assets import router as fixed_assets_router
except Exception:
    fixed_assets_router = None

try:
    from modules.accounting.expenses import router as expenses_router
except Exception:
    expenses_router = None

try:
    from modules.accounting.fixed_asset_statement import router as fixed_asset_statement_router
except Exception:
    fixed_asset_statement_router = None

try:
    from modules.accounting.general_ledger import router as general_ledger_router
except Exception:
    general_ledger_router = None

try:
    from modules.accounting.trial_balance import router as trial_balance_router
except Exception:
    trial_balance_router = None

try:
    from modules.accounting.profit_loss import router as profit_loss_router
except Exception:
    profit_loss_router = None

try:
    from modules.accounting.balance_sheet import router as balance_sheet_router
except Exception:
    balance_sheet_router = None

try:
    from modules.accounting.partner_ledger import router as partner_ledger_router
except Exception:
    partner_ledger_router = None

try:
    from modules.accounting.aging import router as aging_router
except Exception:
    aging_router = None

try:
    from modules.accounting.monthly_dues import router as monthly_dues_router
except Exception:
    monthly_dues_router = None

try:
    from modules.accounting.cost_centers import router as cost_centers_router
except Exception:
    cost_centers_router = None

try:
    from modules.accounting.reports import router as reports_router
except Exception:
    reports_router = None

try:
    from modules.accounting.petty_cash import router as petty_cash_router
except Exception:
    petty_cash_router = None

try:
    from modules.accounting.petty_cash_list import router as petty_cash_list_router
except Exception:
    petty_cash_list_router = None

try:
    from modules.accounting.petty_cash_statement import router as petty_cash_statement_router
except Exception:
    petty_cash_statement_router = None

try:
    from modules.accounting.vendor_payments import router as vendor_payments_router
except Exception:
    vendor_payments_router = None

try:
    from modules.accounting.vendor_statement import router as vendor_statement_router
except Exception:
    vendor_statement_router = None

try:
    from modules.accounting.employee_advances import router as employee_advances_router
except Exception:
    employee_advances_router = None

try:
    from modules.hr.employees import router as employees_router
except Exception:
    employees_router = None

try:
    from modules.hr.categories import router as categories_router
except Exception:
    categories_router = None

try:
    from modules.hr.payroll import router as payroll_router
except Exception:
    payroll_router = None

try:
    from modules.hr.advances import router as advances_router
except Exception:
    advances_router = None

try:
    from modules.hr.attendance import router as attendance_router
except Exception:
    attendance_router = None

try:
    from modules.inventory.goods_receipts import router as goods_receipts_router
except Exception:
    goods_receipts_router = None

try:
    from modules.inventory.items import router as inventory_items_router
except Exception:
    inventory_items_router = None

try:
    from modules.inventory.warehouses import router as inventory_warehouses_router
except Exception:
    inventory_warehouses_router = None

try:
    from modules.inventory.stock import router as inventory_stock_router
except Exception:
    inventory_stock_router = None

try:
    from modules.sales.sales import router as sales_router
except Exception:
    sales_router = None

try:
    from modules.operations.operations import router as operations_router
except Exception:
    operations_router = None

try:
    from modules.purchasing.po_variances import router as po_variances_router
except Exception:
    po_variances_router = None

try:
    from modules.purchasing.purchase_orders import router as purchase_orders_router
except Exception:
    purchase_orders_router = None

try:
    from modules.system.users import router as system_users_router
except Exception:
    system_users_router = None


def include_optional_router(router):
    if router is not None:
        app.include_router(router)


app.include_router(accounts_router)
app.include_router(setup_router)
app.include_router(config_router)
app.include_router(partners_router)
app.include_router(customer_invoices_router)
app.include_router(vendor_bills_router)
app.include_router(journal_router)

include_optional_router(cash_vouchers_router)
include_optional_router(customer_payments_router)
include_optional_router(customer_statement_router)
include_optional_router(expenses_router)
include_optional_router(fixed_asset_statement_router)
include_optional_router(general_ledger_router)
include_optional_router(trial_balance_router)
include_optional_router(profit_loss_router)
include_optional_router(balance_sheet_router)
include_optional_router(partner_ledger_router)
include_optional_router(aging_router)
include_optional_router(monthly_dues_router)
include_optional_router(fixed_assets_router)
include_optional_router(cost_centers_router)
include_optional_router(reports_router)
include_optional_router(petty_cash_router)
include_optional_router(petty_cash_list_router)
include_optional_router(petty_cash_statement_router)
include_optional_router(vendor_payments_router)
include_optional_router(vendor_statement_router)
include_optional_router(employee_advances_router)
include_optional_router(employees_router)
include_optional_router(categories_router)
include_optional_router(attendance_router)
include_optional_router(advances_router)
include_optional_router(payroll_router)
include_optional_router(goods_receipts_router)
include_optional_router(inventory_items_router)
include_optional_router(inventory_warehouses_router)
include_optional_router(inventory_stock_router)
include_optional_router(sales_router)
include_optional_router(operations_router)
include_optional_router(po_variances_router)
include_optional_router(purchase_orders_router)
include_optional_router(system_users_router)
