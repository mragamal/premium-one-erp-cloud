from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from auth import can, default_home_path_for_user
from db import init_db
from layout import render_page

init_db()

app = FastAPI(title="Premium One ERP")

app.add_middleware(
    SessionMiddleware,
    secret_key="premium-one-erp-session-key",
    same_site="lax",
    https_only=False,
)

app.mount("/static", StaticFiles(directory="static"), name="static")


def logged_in(request: Request) -> bool:
    return bool(
        request.session.get("user")
        or request.session.get("username")
        or request.session.get("user_id")
    )


def module_for_path(path: str):
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

    if path.startswith("/api") or any(path.startswith(p) for p in open_paths):
        return await call_next(request)

    if not logged_in(request):
        return RedirectResponse("/login", status_code=302)

    module_code = module_for_path(path)
    if module_code:
        try:
            if not can(request, module_code, "view"):
                return RedirectResponse(default_home_path_for_user(request), status_code=302)
        except Exception:
            pass

    return await call_next(request)


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if logged_in(request):
        return RedirectResponse("/ui/accounting", status_code=302)

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
    username = str(form.get("username") or "").strip()
    password = str(form.get("password") or "").strip()

    if username and password:
        request.session["user"] = {
            "id": 1,
            "username": username,
            "role": "admin",
            "is_admin": True,
        }
        request.session["user_id"] = 1
        request.session["username"] = username
        request.session["role"] = "admin"
        request.session["is_admin"] = True

        return RedirectResponse("/ui/accounting", status_code=303)

    return RedirectResponse("/login", status_code=303)


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
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