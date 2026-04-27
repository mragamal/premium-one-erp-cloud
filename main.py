from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from auth import can, default_home_path_for_user, is_logged_in
from db import init_db
from layout import render_page

init_db()

app = FastAPI(title="Premium One ERP")

app.add_middleware(
    SessionMiddleware,
    secret_key="premium-one-erp-session-key",
    same_site="lax",
)

app.mount("/static", StaticFiles(directory="static"), name="static")


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

    if not is_logged_in(request):
        return RedirectResponse("/login", status_code=302)

    module_code = module_for_path(path)

    if module_code and not can(request, module_code, "view"):
        return RedirectResponse(default_home_path_for_user(request), status_code=302)

    return await call_next(request)


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    content = """
    <div class="card" style="max-width:420px;margin:60px auto;">
        <h2 style="margin-bottom:10px;">Premium One ERP</h2>
        <p style="color:#6d809c;margin-bottom:20px;">Sign in to continue</p>

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
        </form>
    </div>
    """
    return HTMLResponse(render_page("Login", content, "en", current_path="/login"))


@app.post("/login")
async def login_submit(request: Request):
    form = await request.form()
    username = form.get("username")
    password = form.get("password")

    if username and password:
        request.session["user"] = {
            "username": str(username),
            "role": "admin",
            "is_admin": True,
        }
        return RedirectResponse("/ui/accounting", status_code=302)

    return RedirectResponse("/login", status_code=302)


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=302)


@app.get("/")
def root(request: Request):
    if is_logged_in(request):
        return RedirectResponse("/ui/accounting", status_code=302)
    return RedirectResponse("/login", status_code=302)


@app.get("/ui")
def ui_root(request: Request):
    if is_logged_in(request):
        return RedirectResponse("/ui/accounting", status_code=302)
    return RedirectResponse("/login", status_code=302)


@app.get("/test", response_class=HTMLResponse)
def test():
    return "<h2>System Running 🚀</h2>"


from modules.accounting.accounts import router as accounts_router
from modules.accounting.config import router as config_router
from modules.accounting.customer_invoices import router as customer_invoices_router
from modules.accounting.journal import router as journal_router
from modules.accounting.partners import router as partners_router
from modules.accounting.setup import router as setup_router
from modules.accounting.vendor_bills import router as vendor_bills_router


app.include_router(accounts_router)
app.include_router(setup_router)
app.include_router(config_router)
app.include_router(partners_router)
app.include_router(customer_invoices_router)
app.include_router(vendor_bills_router)
app.include_router(journal_router)