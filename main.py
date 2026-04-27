import json
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

# 🔥 NEW API IMPORT
from modules.api.customers_api import router as customers_api_router

init_db()

app = FastAPI(title="Premium One ERP")

app.add_middleware(
    SessionMiddleware,
    secret_key="premium-one-erp-session-key",
    same_site="lax",
)

app.mount("/static", StaticFiles(directory="static"), name="static")

session_signer = TimestampSigner("premium-one-erp-session-key")


# 🔥 MODULE DETECTION
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
    ]
    for prefix, module_code in rules:
        if path.startswith(prefix):
            return module_code
    return None


# 🔐 SESSION HANDLING
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


# 🔥 AUTH MIDDLEWARE (UPDATED)
@app.middleware("http")
async def auth_guard(request: Request, call_next):
    path = request.url.path or ""

    # ✅ IMPORTANT: Allow API without login (temporary for testing)
    if path.startswith("/api"):
        return await call_next(request)

    open_paths = ["/login", "/logout", "/static", "/favicon.ico"]

    if any(path.startswith(prefix) for prefix in open_paths):
        return await call_next(request)

    hydrate_session_from_cookie(request)

    if not is_logged_in(request):
        return RedirectResponse("/login", status_code=302)

    module_code = module_for_path(path)

    if module_code and not can(request, module_code, "view"):
        return RedirectResponse(default_home_path_for_user(request), status_code=302)

    return await call_next(request)


# 🔥 BASIC ROUTES
@app.get("/")
def root(request: Request):
    return RedirectResponse(default_home_path_for_user(request), status_code=302)


@app.get("/ui")
def ui_root(request: Request):
    return RedirectResponse(default_home_path_for_user(request), status_code=302)


# 🔥 TEST PAGE
@app.get("/test", response_class=HTMLResponse)
def test():
    return "<h2>System Running 🚀</h2>"


# =========================
# 🔥 INCLUDE ROUTERS
# =========================

# 🧠 CORE MODULES
from modules.accounting.accounts import router as accounts_router
from modules.accounting.config import router as config_router
from modules.accounting.customer_invoices import router as customer_invoices_router
from modules.accounting.journal import router as journal_router
from modules.accounting.partners import router as partners_router
from modules.accounting.setup import router as setup_router
from modules.accounting.vendor_bills import router as vendor_bills_router

# 🔥 INCLUDE CORE
app.include_router(accounts_router)
app.include_router(setup_router)
app.include_router(config_router)
app.include_router(partners_router)
app.include_router(customer_invoices_router)
app.include_router(vendor_bills_router)
app.include_router(journal_router)

# 🔥 INCLUDE NEW API
app.include_router(customers_api_router)