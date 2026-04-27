translations = {
    "en": {
        "app_name": "Premium One ERP",
        "configuration": "Configuration",
        "accounts": "Accounts",
        "journals": "Journals",
        "customers": "Customers",
        "vendors": "Vendors",
        "employees": "Employees",
        "petty_cash": "Petty Cash",
        "expenses": "Expenses",
        "statement": "Statement",
        "customer_invoices": "Customer Invoices",
        "customer_payments": "Customer Payments",
    }
}


def t(key, lang="en"):
    return translations.get("en", {}).get(key, key)


def get_lang(request):
    try:
        lang = (request.query_params.get("lang") or "").strip().lower()
        if lang in ["ar", "en"]:
            return lang
    except Exception:
        pass
    return "en"
