from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from db import init_db
from layout import render_page

# Optional auth helpers from your project. If any helper fails on Render,
# this main.py still keeps the system running.
try:
    from auth import can, is_logged_in, default_home_path_for_user
except Exception:
    can = None
    is_logged_in = None
    default_home_path_for_user = None


init_db()

app = FastAPI(title="Premium One ERP")

# IMPORTANT: SessionMiddleware must be added before using request.session anywhere.
app.add_middleware(
    SessionMiddleware,
    secret_key="premium-one-erp-session-key-change-later",
    same_site="lax",
    https_only=True,
)

app.mount("/static", StaticFiles(directory="static"), name="static")


def safe_session(request: Request) -> dict:
    """Return session safely even if middleware is unavailable for any reason."""
    try:
        return request.session
    except AssertionError:
        return {}


def logged_in(request: Request) -> bool:
    """Robust login check for Render testing and normal app usage."""
    session = safe_session(request)
    if session.get("logged_in") or session.get("user") or session.get("user_id"):
        return True

    if is_logged_in is not None:
        try:
            return bool(is_logged_in(request))
        except Exception:
            return False

    return False


def user_can(request: Request, module_code: str, action: str = "view") -> bool:
    """Temporary permissive permission wrapper until production auth is finalized."""
    if can is None:
        return True
    try:
        return bool(can(request, module_code, action))
    except Exception:
        return True


def home_path(request: Request) -> str:
    if default_home_path_for_user is not None:
        try:
            path = default_home_path_for_user(request)
            if path:
                return path
        except Exception:
            pass
    return "/ui/accounting"


def module_for_path(path: str):
    path = path or ""
    rules = [
        ("/ui/settings", "system"),
        ("/ui/system/users", "users"),
        ("/ui/accounting", "accounting"),
        ("/ui/hr", "hr"),
        ("/ui/inventory", "inventory"),
        ("/ui/purchasing", "purchasing"),
        ("/ui/sales", "sales"),
        ("/ui/operations", "operations"),
        ("/ui/projects", "operations"),
    ]
    for prefix, module_code in rules:
        if path.startswith(prefix):
            return module_code
    return None


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

    if not logged_in(request):
        return RedirectResponse("/login", status_code=302)

    module_code = module_for_path(path)
    if module_code and not user_can(request, module_code, "view"):
        return RedirectResponse(home_path(request), status_code=302)

    return await call_next(request)


def t(lang: str, en: str, ar: str) -> str:
    return ar if lang == "ar" else en


def dashboard_cards(cards):
    html = '<div class="card-grid">'
    for title, href, icon, desc in cards:
        icon_html = f'<img src="{icon}" alt="{title} icon">' if str(icon).startswith("/static/") else icon
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


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    error = request.query_params.get("error")
    error_html = ""
    if error:
        error_html = '<div class="msg error">Invalid login attempt.</div>'

    content = f"""
    <div class="card" style="max-width:460px;margin:60px auto;">
        <h2 style="margin-bottom:10px;">Premium One ERP</h2>
        <p style="color:#6d809c;margin-bottom:20px;">Sign in to continue</p>
        {error_html}
        <form method="post" action="/login">
            <div class="form-group">
                <label>Username</label>
                <input name="username" placeholder="Enter username" required>
            </div>
            <div class="form-group" style="margin-top:12px;">
                <label>Password</label>
                <input name="password" type="password" placeholder="Enter password" required>
            </div>
            <div class="form-actions" style="margin-top:20px;">
                <button class="btn blue" type="submit" style="width:100%;">Login</button>
            </div>
            <p style="color:#6d809c;margin-top:14px;font-size:13px;">
                Temporary Render login: use any username and password.
            </p>
        </form>
    </div>
    """
    return HTMLResponse(render_page("Login", content, "en", current_path="/login"))


@app.post("/login")
async def login_submit(request: Request):
    form = await request.form()
    username = str(form.get("username") or "").strip()
    password = str(form.get("password") or "").strip()

    if not username or not password:
        return RedirectResponse("/login?error=1", status_code=303)

    session = safe_session(request)
    session.clear()
    session["logged_in"] = True
    session["user_id"] = 1
    session["username"] = username
    session["role"] = "admin"
    session["is_admin"] = True
    session["user"] = {
        "id": 1,
        "username": username,
        "name": username,
        "role": "admin",
        "is_admin": True,
    }

    return RedirectResponse("/ui/accounting", status_code=303)


@app.get("/logout")
def logout(request: Request):
    safe_session(request).clear()
    return RedirectResponse("/login", status_code=302)


@app.get("/")
def root(request: Request):
    if logged_in(request):
        return RedirectResponse("/ui/accounting", status_code=302)
    return RedirectResponse("/login", status_code=302)


@app.get("/ui")
def ui_root(request: Request):
    if logged_in(request):
        return RedirectResponse("/ui/accounting", status_code=302)
    return RedirectResponse("/login", status_code=302)


@app.get("/test", response_class=HTMLResponse)
def test():
    return "<h2>System Running 🚀</h2>"


@app.get("/ui/settings", response_class=HTMLResponse)
def settings_root(request: Request):
    content = """
    <div class="card">
        <h2>Settings</h2>
        <p style="color:#6d809c; margin-top:8px;">General system settings.</p>
    </div>
    """
    return HTMLResponse(render_page("Settings", content, "en", current_path="/ui/settings"))


@app.get("/ui/accounting", response_class=HTMLResponse)
def accounting_root(request: Request):
    cards = [
        ("System Setup", "/ui/accounting/setup", "/static/icons/system-setup.svg", "Company and system initialization"),
        ("Configuration", "/ui/accounting/config", "/static/icons/configuration.svg", "Default accounts and prefixes"),
        ("Chart of Accounts", "/ui/accounting/accounts", "/static/icons/chart-accounts.svg", "Manage account structure"),
        ("Cost Centers", "/ui/accounting/cost-centers", "/static/icons/cost-centers.svg", "Department and activity allocation"),
        ("Customers", "/ui/accounting/customers-hub", "/static/icons/customers.svg", "Customer master and transactions"),
        ("Vendors", "/ui/accounting/vendors-hub", "/static/icons/vendors.svg", "Vendor master and transactions"),
        ("Journal", "/ui/accounting/journal", "/static/icons/journal.svg", "Journal entries and review"),
        ("Expenses", "/ui/accounting/expenses", "/static/icons/expenses.svg", "Operational expenses and posting"),
        ("Cash Receipts", "/ui/accounting/cash-receipts", "/static/icons/customer-payments.svg", "Cash receipt vouchers"),
        ("Cash Payments", "/ui/accounting/cash-payments", "/static/icons/vendor-payments.svg", "Cash payment vouchers"),
        ("Petty Cash", "/ui/accounting/petty-cash", "/static/icons/petty-cash.svg", "Custody and returns"),
        ("Fixed Assets", "/ui/accounting/fixed-assets", "/static/icons/fixed-assets.svg", "Assets and depreciation"),
        ("Reports", "/ui/accounting/reports", "/static/icons/reports.svg", "Financial reports"),
    ]
    content = card_section("Accounting", cards)
    return HTMLResponse(render_page("Accounting", content, "en", current_path="/ui/accounting"))


@app.get("/ui/accounting/customers-hub", response_class=HTMLResponse)
def customers_hub(request: Request):
    cards = [
        ("Customers", "/ui/accounting/customers", "/static/icons/customers.svg", "Customer master data"),
        ("Customer Invoices", "/ui/accounting/customer-invoices", "/static/icons/customer-invoices.svg", "Sales invoices"),
        ("Customer Statement", "/ui/accounting/customer-statement", "/static/icons/customer-statement.svg", "Account statement and balances"),
    ]
    return HTMLResponse(render_page("Customers", card_section("Customers", cards), "en", current_path="/ui/accounting/customers-hub"))


@app.get("/ui/accounting/vendors-hub", response_class=HTMLResponse)
def vendors_hub(request: Request):
    cards = [
        ("Vendors", "/ui/accounting/vendors", "/static/icons/vendors.svg", "Vendor master data"),
        ("Vendor Bills", "/ui/accounting/vendor-bills", "/static/icons/vendor-bills.svg", "Purchase bills"),
        ("Vendor Statement", "/ui/accounting/vendor-statement", "/static/icons/vendor-statement.svg", "Account statement and balances"),
    ]
    return HTMLResponse(render_page("Vendors", card_section("Vendors", cards), "en", current_path="/ui/accounting/vendors-hub"))


@app.get("/ui/hr", response_class=HTMLResponse)
def hr_root(request: Request):
    cards = [
        ("Employees", "/ui/hr/employees", "/static/icons/employees.svg", "Employee master data"),
        ("Employee Categories", "/ui/hr/categories", "/static/icons/employees.svg", "Attendance groups and rules"),
        ("Attendance", "/ui/hr/attendance", "/static/icons/reports.svg", "Attendance import and logs"),
        ("Payroll", "/ui/hr/payroll", "/static/icons/reports.svg", "Monthly payroll"),
    ]
    return HTMLResponse(render_page("HR", card_section("HR", cards), "en", current_path="/ui/hr"))


@app.get("/ui/inventory", response_class=HTMLResponse)
def inventory_root(request: Request):
    cards = [
        ("Items", "/ui/inventory/items", "/static/icons/items.svg", "Item master"),
        ("Warehouses", "/ui/inventory/warehouses", "/static/icons/warehouses.svg", "Warehouse structure"),
        ("Goods Receipts", "/ui/inventory/goods-receipts", "/static/icons/goods-receipts.svg", "Receiving"),
        ("Stock Balance", "/ui/inventory/stock-balance", "/static/icons/stock-balance.svg", "Current stock"),
        ("Stock Ledger", "/ui/inventory/stock-ledger", "/static/icons/stock-ledger.svg", "Movement history"),
    ]
    return HTMLResponse(render_page("Inventory", card_section("Inventory", cards), "en", current_path="/ui/inventory"))


@app.get("/ui/purchasing", response_class=HTMLResponse)
def purchasing_root(request: Request):
    cards = [
        ("Purchase Orders", "/ui/purchasing/purchase-orders", "/static/icons/purchase-orders.svg", "Purchase orders"),
        ("PO Variances", "/ui/purchasing/po-variances", "/static/icons/po-variances.svg", "Review variances"),
    ]
    return HTMLResponse(render_page("Purchasing", card_section("Purchasing", cards), "en", current_path="/ui/purchasing"))


@app.get("/ui/sales", response_class=HTMLResponse)
def sales_root(request: Request):
    content = '<div class="card"><h2>Sales</h2><p>Sales module is running.</p></div>'
    return HTMLResponse(render_page("Sales", content, "en", current_path="/ui/sales"))


@app.get("/ui/operations", response_class=HTMLResponse)
def operations_root(request: Request):
    content = '<div class="card"><h2>Operations</h2><p>Operations module is running.</p></div>'
    return HTMLResponse(render_page("Operations", content, "en", current_path="/ui/operations"))


# Include module routers safely. If one router fails, Render will not crash.
def include_router_safely(import_path: str, router_name: str = "router"):
    try:
        module_path, attr = import_path.rsplit(".", 1)
        module = __import__(module_path, fromlist=[attr])
        router = getattr(module, attr)
        app.include_router(router)
        print(f"Included router: {import_path}", flush=True)
    except Exception as exc:
        print(f"Skipped router {import_path}: {exc}", flush=True)


ROUTERS = [
    "modules.accounting.accounts.router",
    "modules.accounting.setup.router",
    "modules.accounting.config.router",
    "modules.accounting.partners.router",
    "modules.accounting.customer_invoices.router",
    "modules.accounting.vendor_bills.router",
    "modules.accounting.journal.router",
    "modules.accounting.cash_vouchers.router",
    "modules.accounting.customer_payments.router",
    "modules.accounting.customer_statement.router",
    "modules.accounting.expenses.router",
    "modules.accounting.fixed_assets.router",
    "modules.accounting.cost_centers.router",
    "modules.accounting.reports.router",
    "modules.accounting.petty_cash.router",
    "modules.accounting.petty_cash_list.router",
    "modules.accounting.petty_cash_statement.router",
    "modules.accounting.vendor_payments.router",
    "modules.accounting.vendor_statement.router",
    "modules.accounting.employee_advances.router",
    "modules.hr.employees.router",
    "modules.hr.categories.router",
    "modules.hr.attendance.router",
    "modules.hr.advances.router",
    "modules.hr.payroll.router",
    "modules.inventory.goods_receipts.router",
    "modules.inventory.items.router",
    "modules.inventory.warehouses.router",
    "modules.inventory.stock.router",
    "modules.sales.sales.router",
    "modules.operations.operations.router",
    "modules.purchasing.po_variances.router",
    "modules.purchasing.purchase_orders.router",
    "modules.system.users.router",
]

for router_path in ROUTERS:
    include_router_safely(router_path)
