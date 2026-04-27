import inspect
from pathlib import Path

from auth import can


_I18N_PATH = Path(__file__).resolve().parent / "static" / "js" / "i18n.js"
_I18N_JS_VERSION = str(int(_I18N_PATH.stat().st_mtime_ns)) if _I18N_PATH.exists() else "1"
def _request_from_stack():
    try:
        for frame_info in inspect.stack()[1:10]:
            request = frame_info.frame.f_locals.get("request")
            if request is not None and hasattr(request, "session"):
                return request
    except Exception:
        return None
    return None


def _sidebar_menu_items(request, current_path=""):
    lang = "en"
    if request and "lang" in request.query_params:
        lang = request.query_params["lang"]
    elif request and "ui_lang" in request.cookies:
        lang = request.cookies["ui_lang"]

    items = [
        ("accounting", "/ui/accounting", "/static/icons/nav-accounting.svg", "Accounting"),
        ("hr", "/ui/hr", "/static/icons/nav-hr.svg", "HR"),
        ("inventory", "/ui/inventory", "/static/icons/nav-inventory.svg", "Inventory"),
        ("purchasing", "/ui/purchasing", "/static/icons/nav-purchasing.svg", "Purchasing"),
        ("sales", "/ui/sales", "/static/icons/nav-sales.svg", "Sales"),
        ("operations", "/ui/operations", "/static/icons/nav-projects.svg", "Operations"),
        ("users", "/ui/system/users", "/static/icons/employees.svg", "Users"),
    ]

    html = []
    for module_code, href, icon, label in items:
        if request and not can(request, module_code, "view"):
            continue

        active = href in current_path
        html.append(f"""
        <a class="menu-item {'active' if active else ''}" href="{href}">
            <span class="menu-icon"><img src="{icon}"></span>
            <span class="menu-text">{label}</span>
        </a>
        """)
    return "".join(html)


def render_page(title, content, lang="en", current_path=""):
    request = _request_from_stack()
    sidebar_items_html = _sidebar_menu_items(request, current_path)

    return f"""
<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>

<!-- 🔥 PWA -->
<link rel="manifest" href="/static/manifest.json">
<meta name="theme-color" content="#052861">
<link rel="apple-touch-icon" href="/static/logo6.png">

<style>
body {{
    margin:0;
    font-family: Arial;
    background:#f4f6f9;
}}

.app {{
    display:flex;
}}

.sidebar {{
    width:250px;
    background:#052861;
    color:#fff;
    height:100vh;
    padding:15px;
}}

.menu-item {{
    display:flex;
    padding:10px;
    color:#fff;
}}

.main {{
    flex:1;
    padding:20px;
}}

.card {{
    background:#fff;
    padding:15px;
    border-radius:10px;
    margin-bottom:15px;
}}

.card-grid {{
    display:grid;
    grid-template-columns:repeat(4,1fr);
    gap:10px;
}}

.module-card {{
    padding:15px;
    background:#fff;
    border-radius:10px;
}}

.topbar {{
    background:#fff;
    padding:10px;
    border-radius:10px;
    margin-bottom:10px;
}}

/* 🔥 MOBILE FIX */
@media (max-width:900px) {{
    .sidebar {{ display:none; }}
    .card-grid {{ grid-template-columns:1fr; }}
    .main {{ padding:10px; }}
}}
</style>
</head>

<body>

<div class="app">

<div class="sidebar">
{sidebar_items_html}
</div>

<div class="main">

<div class="topbar">
<h2>{title}</h2>
</div>

{content}

</div>
</div>

<!-- 🔥 SERVICE WORKER + INSTALL -->
<script>
if ('serviceWorker' in navigator) {{
    navigator.serviceWorker.register('/static/sw.js');
}}

let deferredPrompt;

window.addEventListener('beforeinstallprompt', (e) => {{
    e.preventDefault();
    deferredPrompt = e;

    const btn = document.createElement("button");
    btn.innerText = "Install App";
    btn.style.position = "fixed";
    btn.style.bottom = "20px";
    btn.style.right = "20px";
    btn.style.background = "#2a67ea";
    btn.style.color = "#fff";
    btn.style.padding = "10px";
    btn.style.borderRadius = "10px";

    btn.onclick = () => {{
        deferredPrompt.prompt();
    }};

    document.body.appendChild(btn);
}});
</script>

</body>
</html>
"""