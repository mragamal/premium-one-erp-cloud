(function () {
    const exact = {
        "Home": "الرئيسية",
        "Users": "المستخدمون",
        "User": "المستخدم",
        "New User": "مستخدم جديد",
        "Full Name": "الاسم الكامل",
        "Permissions": "الصلاحيات",
        "Administrator": "مدير النظام",
        "System Administrator": "مدير النظام",
        "Inactive": "غير نشط",
        "User Permissions": "صلاحيات المستخدم",
        "Accessible Modules": "الموديولات المتاحة",
        "Module": "الموديول",
        "View": "عرض",
        "Create": "إنشاء",
        "Approve": "اعتماد",
        "Save Permissions": "حفظ الصلاحيات",
        "Select Role": "اختر الدور",
        "Username already exists.": "اسم المستخدم موجود بالفعل.",
        "Logout": "تسجيل الخروج",
        "Arabic": "عربي",
        "Accounting": "الحسابات",
        "HR": "الموارد البشرية",
        "Inventory": "المخازن",
        "Purchasing": "المشتريات",
        "Sales": "المبيعات",
        "Projects": "المشروعات",
        "Settings": "الإعدادات",
        "System Setup": "تهيئة النظام",
        "Configuration": "الإعدادات العامة",
        "Chart of Accounts": "شجرة الحسابات",
        "Cost Centers": "مراكز التكلفة",
        "Customers": "العملاء",
        "Vendors": "الموردون",
        "Journal": "دفتر اليومية",
        "Expenses": "المصروفات",
        "Petty Cash": "العهدة النقدية",
        "Fixed Assets": "الأصول الثابتة",
        "Reports": "التقارير",
        "Employee Categories": "فئات الموظفين",
        "Employees": "الموظفون",
        "Attendance": "الحضور والانصراف",
        "Payroll": "المرتبات",
        "Items": "الأصناف",
        "Warehouses": "المخازن",
        "Goods Receipts": "أذون الاستلام",
        "Stock Balance": "رصيد المخزون",
        "Stock Ledger": "حركة المخزون",
        "Purchase Orders": "أوامر الشراء",
        "PO Variances": "فروقات أوامر الشراء",
        "Quotations": "عروض الأسعار",
        "Sales Orders": "أوامر البيع",
        "Deliveries": "التسليمات",
        "Delivery Notes": "أذون التسليم",
        "Customer Invoices": "فواتير العملاء",
        "Customer Payments": "تحصيلات العملاء",
        "Customer Receipts": "تحصيلات العملاء",
        "Customer Statement": "كشف حساب العميل",
        "Invoices": "الفواتير",
        "Sales Module": "موديول المبيعات",
        "Sales Workspace": "مساحة عمل المبيعات",
        "Fixed Asset Acquisition": "اقتناء أصل ثابت",
        "Customer Bill": "فاتورة عميل",
        "Vendor Bills": "فواتير الموردين",
        "Vendor Payments": "مدفوعات الموردين",
        "Vendor Statement": "كشف حساب المورد",
        "Filters": "الفلاتر",
        "Filter": "تصفية",
        "Clear": "مسح",
        "Search": "بحث",
        "Category": "الفئة",
        "All Categories": "كل الفئات",
        "All": "الكل",
        "Draft": "مسودة",
        "Posted": "مرحل",
        "Reversed": "معكوس",
        "Open": "فتح",
        "Edit": "تعديل",
        "Delete": "حذف",
        "Save": "حفظ",
        "Save Draft": "حفظ كمسودة",
        "Back": "رجوع",
        "Template": "النموذج",
        "Import Excel": "استيراد إكسل",
        "Export Excel": "تصدير إكسل",
        "+ New Entry": "+ قيد جديد",
        "+ New Employee": "+ موظف جديد",
        "+ New Category": "+ فئة جديدة",
        "+ New Invoice": "+ فاتورة جديدة",
        "+ New Item": "+ صنف جديد",
        "+ New Customer": "+ عميل جديد",
        "+ New Vendor": "+ مورد جديد",
        "+ New Payroll Run": "+ تشغيل مرتبات جديد",
        "Entries": "القيود",
        "Debit": "مدين",
        "Credit": "دائن",
        "Entry No": "رقم القيد",
        "Date": "التاريخ",
        "From Date": "من تاريخ",
        "To Date": "إلى تاريخ",
        "Description": "البيان",
        "Reference": "المرجع",
        "Status": "الحالة",
        "Actions": "الإجراءات",
        "Total Debit": "إجمالي المدين",
        "Total Credit": "إجمالي الدائن",
        "Entry Date": "تاريخ القيد",
        "Balance Check": "فحص التوازن",
        "Balanced": "متوازن",
        "Unbalanced": "غير متوازن",
        "Lines": "السطور",
        "Journal Entries": "قيود اليومية",
        "Journal Entry": "قيد يومية",
        "Journal Lines": "سطور القيد",
        "Account": "الحساب",
        "Remove": "حذف",
        "Add Line": "إضافة سطر",
        "Import Journal": "استيراد اليومية",
        "Import Journal Entries": "استيراد قيود اليومية",
        "Import as Draft": "استيراد كمسودة",
        "Download Template": "تحميل النموذج",
        "Excel File": "ملف إكسل",
        "New Journal Entry": "قيد يومية جديد",
        "Edit Journal Entry": "تعديل قيد اليومية",
        "Post": "ترحيل",
        "Reverse": "عكس",
        "Manual": "يدوي",
        "Reversal": "عكس قيد",
        "Customer Invoice": "فاتورة عميل",
        "Vendor Bill": "فاتورة مورد",
        "Customer Payment": "تحصيل عميل",
        "Vendor Payment": "سداد مورد",
        "Fixed Asset": "أصل ثابت",
        "Depreciation": "إهلاك",
        "Asset Disposal": "استبعاد أصل",
        "Code": "الكود",
        "Name": "الاسم",
        "Phone": "الهاتف",
        "Email": "البريد الإلكتروني",
        "Address": "العنوان",
        "Tax No": "الرقم الضريبي",
        "Payment Term": "مدة السداد",
        "Payment Term Days": "مدة السداد بالأيام",
        "Opening Balance": "الرصيد الافتتاحي",
        "Active": "نشط",
        "Inactive": "غير نشط",
        "Biometric": "كود البصمة",
        "Employee Name": "اسم الموظف",
        "Employee Category": "فئة الموظف",
        "Department": "القسم",
        "Job Title": "الوظيفة",
        "Hire Date": "تاريخ التعيين",
        "National ID": "الرقم القومي",
        "Payroll Setup": "إعدادات المرتب",
        "Basic Salary": "الراتب الأساسي",
        "Housing Allowance": "بدل السكن",
        "Transport Allowance": "بدل الانتقال",
        "Other Allowance": "بدلات أخرى",
        "Insurance Applicable": "خاضع للتأمين",
        "Insurance Number": "رقم التأمين",
        "Insurance Salary": "راتب التأمين",
        "Employee Insurance Rate %": "نسبة تأمين الموظف %",
        "Employer Insurance Rate %": "نسبة تأمين الشركة %",
        "Payment Method": "طريقة السداد",
        "Bank Transfer": "تحويل بنكي",
        "Cash": "نقدي",
        "Bank Name": "اسم البنك",
        "Bank Account": "حساب البنك",
        "Expected Daily Hours": "ساعات العمل اليومية",
        "Total Package": "إجمالي الراتب",
        "Import Employees (CSV / XLSX)": "استيراد الموظفين (CSV / XLSX)",
        "Import": "استيراد",
        "Attendance Role": "دور الحضور",
        "Shift Start": "بداية الشيفت",
        "Shift End": "نهاية الشيفت",
        "Daily Hours": "الساعات اليومية",
        "Late Grace": "سماح التأخير",
        "Early Leave Grace": "سماح الانصراف المبكر",
        "Attendance Days": "أيام الحضور",
        "Absent Days": "أيام الغياب",
        "Worked Hours": "ساعات العمل",
        "Overtime Hours": "ساعات إضافية",
        "Attendance": "الحضور والانصراف",
        "Import Attendance": "استيراد الحضور",
        "Import Attendance / Biometric File": "استيراد ملف الحضور / البصمة",
        "Check In": "وقت الحضور",
        "Check Out": "وقت الانصراف",
        "Late Min": "دقائق التأخير",
        "Early Leave Min": "دقائق الانصراف المبكر",
        "Payroll No": "رقم المسير",
        "Payroll Month": "شهر المرتب",
        "Payroll Year": "سنة المرتب",
        "Payment Date": "تاريخ السداد",
        "Period From": "الفترة من",
        "Period To": "الفترة إلى",
        "Working Days Basis": "أساس أيام العمل",
        "Notes": "ملاحظات",
        "Gross": "إجمالي الاستحقاق",
        "Deductions": "الاستقطاعات",
        "Net": "الصافي",
        "Bonus": "مكافأة",
        "Deduction": "خصم",
        "Advance": "سلفة",
        "Absence": "غياب",
        "Comp. Insurance": "تأمين الشركة",
        "Emp. Insurance": "تأمين الموظف",
        "Overtime": "إضافي",
        "Month": "الشهر",
        "Employees imported:": "تم استيراد الموظفين:",
        "Skipped:": "تم التخطي:",
        "Items": "الأصناف",
        "UOM": "وحدة القياس",
        "Type": "النوع",
        "New Item": "صنف جديد",
        "Item": "الصنف",
        "Qty": "الكمية",
        "Unit Price": "سعر الوحدة",
        "Total": "الإجمالي",
        "Warehouse": "المخزن",
        "Goods Receipt": "إذن استلام",
        "Receipt Lines": "سطور الاستلام",
        "Save Receipt": "حفظ الاستلام",
        "PO No": "رقم أمر الشراء",
        "PO Date": "تاريخ أمر الشراء",
        "Vendor": "المورد",
        "PO Lines": "سطور أمر الشراء",
        "New Purchase Order": "أمر شراء جديد",
        "Approve": "اعتماد",
        "Reject": "رفض",
        "Approved": "معتمد",
        "Pending": "قيد الاعتماد",
        "Rejected": "مرفوض",
        "Quotation No": "رقم عرض السعر",
        "Quotation Date": "تاريخ عرض السعر",
        "Valid Until": "صالح حتى",
        "Sales Order No": "رقم أمر البيع",
        "Sales Order Date": "تاريخ أمر البيع",
        "Delivery No": "رقم إذن التسليم",
        "Delivery Date": "تاريخ إذن التسليم",
        "Source Quotation": "عرض السعر المصدر",
        "Source Sales Order": "أمر البيع المصدر",
        "Customer": "العميل",
        "Customer Receipts": "تحصيلات العملاء",
        "Statement": "كشف الحساب",
        "Secure & Reliable": "آمن وموثوق",
        "Fast & Efficient": "سريع وفعال",
        "Smart Reporting": "تقارير ذكية",
        "Cloud Based": "سحابي",
        "Welcome Back": "مرحبًا بعودتك",
        "Username": "اسم المستخدم",
        "Password": "كلمة المرور",
        "Sign In": "تسجيل الدخول",
        "Forgot Password?": "هل نسيت كلمة المرور؟",
        "Sign in with SSO": "تسجيل الدخول عبر SSO",
        "Select": "اختيار",
        "Open Full Page": "فتح كامل الصفحة",
        "Reports Center": "مركز التقارير",
        "Reports Home": "الرئيسية",
        "General Ledger": "الأستاذ العام",
        "Trial Balance": "ميزان المراجعة",
        "Profit & Loss": "الأرباح والخسائر",
        "Balance Sheet": "الميزانية العمومية",
        "Partner Ledger": "أستاذ الأطراف",
        "Aging": "الاعمار الزمنية",
        "Aging Report": "تقرير الأعمار",
        "Monthly Dues": "استحقاقات شهرية",
        "Petty Cash Statement": "كشف العهدة النقدية",
        "Asset Register": "سجل الأصول",
        "Customers": "العملاء",
        "Manage customer master data.": "إدارة البيانات الأساسية للعملاء.",
        "Manage vendor master data.": "إدارة البيانات الأساسية للموردين.",
        "Orange": "أورانج",
        "watan electric": "وطن إلكتريك",
        "Payment Status": "حالة السداد",
        "Document Status": "حالة المستند",
        "All Customers": "كل العملاء",
        "All Document Status": "كل حالات المستند",
        "All Payment Status": "كل حالات السداد",
        "Invoice #": "رقم الفاتورة",
        "Invoice Date": "تاريخ الفاتورة",
        "Due Date": "تاريخ الاستحقاق",
        "Total Amount": "إجمالي المبلغ",
        "Paid Amount": "المبلغ المدفوع",
        "Balance": "الرصيد",
        "Paid": "مدفوع",
        "Partial": "جزئي",
        "Cancelled": "ملغاة",
        "New Invoice": "فاتورة جديدة",
        "Post": "ترحيل",
        "Report": "تقرير",
        "Accounting Reports": "تقارير الحسابات",
        "Reports Center": "مركز التقارير",
        "Selected: General Ledger": "المحدد: الأستاذ العام",
        "9 Reports": "9 تقارير",
        "Assets, liabilities, and equity.": "الأصول والالتزامات وحقوق الملكية.",
        "Asset register, depreciation, and movement statement.": "سجل الأصول والإهلاك وبيان الحركة.",
        "Customer, vendor, and employee partner movements.": "حركات العملاء والموردين والموظفين.",
        "Due invoices and bills by month.": "الفواتير المستحقة حسب الشهر.",
        "Employee custody statement and movement balance.": "كشف عهد الموظف ورصيد الحركة.",
        "Posted journals by account with running balance.": "القيود المرحلة حسب الحساب مع الرصيد الجاري.",
        "Open receivables and payables by age bucket.": "المدينون والدائنون المفتوحون حسب فترات الاستحقاق.",
        "Opening, period, and closing balances.": "الأرصدة الافتتاحية والحركة والختامية.",
        "Revenue, cost of revenue, and operating expenses.": "الإيرادات وتكلفة الإيراد والمصروفات التشغيلية.",
        "Category": "الفئة",
        "Role": "الدور",
        "Action": "الإجراء",
        "Import Items (CSV / XLSX)": "استيراد الأصناف (CSV / XLSX)",
        "Yes": "نعم",
        "No": "لا",
        "Main Warehouse": "المخزن الرئيسي",
        "Warehouse Code": "كود المخزن",
        "Warehouse Name": "اسم المخزن",
        "Balance Qty": "الكمية المتاحة",
        "Item Code": "كود الصنف",
        "Item Name": "اسم الصنف",
        "Total Qty": "إجمالي الكمية",
        "Running Balance": "الرصيد الجاري",
        "Qty In": "وارد",
        "Qty Out": "منصرف",
        "Goods Receipts": "أذون الاستلام",
        "New Receipt": "إذن استلام جديد",
        "GRN No": "رقم إذن الاستلام",
        "Approval": "الاعتماد",
        "Workflow": "سير العمل",
        "Mark Read": "تحديد كمقروء",
        "Ready For Vendor Bill": "جاهز لفاتورة المورد",
        "Receipt Variance Detected": "تم اكتشاف فرق استلام",
        "Review Variances": "مراجعة الفروقات",
        "Purchasing Workflow Alerts": "تنبيهات سير عمل المشتريات",
        "New PO": "أمر شراء جديد",
        "Open PO": "فتح أمر الشراء",
        "PO No": "رقم أمر الشراء",
        "PO Approved": "تم اعتماد أمر الشراء",
        "PO Draft Created": "تم إنشاء أمر شراء كمسودة",
        "PO Pending Approval": "أمر الشراء بانتظار الاعتماد",
        "Warehouse Receipt Posted": "تم ترحيل استلام المخزن",
        "received": "تم الاستلام",
        "posted": "مرحل",
        "stock_item": "صنف مخزني",
        "goods_receipt": "إذن استلام",
        "Sales Workspace": "مساحة عمل المبيعات",
        "Sales Module": "موديول المبيعات",
        "Run the commercial cycle from quotation to sales order and delivery, with direct access to customer invoices, collections, and statements from the same place.": "شغّل دورة البيع من عرض السعر إلى أمر البيع ثم التسليم، مع وصول مباشر لفواتير العملاء والتحصيلات وكشوف الحساب من نفس المكان.",
        "Back to Sales": "العودة إلى المبيعات",
        "Create and manage customer quotations before sales confirmation.": "إنشاء وإدارة عروض أسعار العملاء قبل تأكيد البيع.",
        "Confirmed commercial orders ready for delivery and invoicing.": "أوامر بيع مؤكدة جاهزة للتسليم والفوترة.",
        "Deliver goods against the sales order and prepare for invoicing or operations handoff.": "تسليم البضاعة مقابل أمر البيع وتجهيزها للفوترة أو التسليم للتشغيل.",
        "Quotation": "عرض السعر",
        "Sales Order": "أمر البيع",
        "Delivery No": "رقم إذن التسليم",
        "Operations": "التشغيل",
        "Contract Companies": "الشركات المتعاقدة",
        "Fault Types": "أنواع الأعطال",
        "Fault Type": "نوع العطل",
        "Fault Type List": "قائمة أنواع الأعطال",
        "Fault Name": "اسم العطل",
        "Known fault names used when opening tickets. Pricing and incentive should be configured on the Action side.": "أسماء الأعطال المستخدمة عند فتح التيكت. التسعير والحافز يتم ضبطهما من شاشة الأكشن.",
        "Known fault codes used when opening tickets and classifying field issues.": "أكواد الأعطال المستخدمة عند فتح التيكتات وتصنيف المشاكل الميدانية.",
        "Action Catalog": "دليل الأكشنات",
        "Vehicle Rates": "تسعير السيارات",
        "Vehicle Rate List": "قائمة تسعير السيارات",
        "Vehicles": "السيارات",
        "Rental Offices": "مكاتب التأجير",
        "Tickets": "التيكتات",
        "Contracts": "العقود",
        "Pricing Versions": "إصدارات التسعير",
        "Trip Tickets": "تيكتات الرحلات",
        "Trip Register": "سجل الرحلات",
        "New Draft Trip": "رحلة مسودة جديدة",
        "Trip Ticket": "تيكت الرحلة",
        "Trip No": "رقم الرحلة",
        "Trip Date": "تاريخ الرحلة",
        "Vehicle Code": "كود السيارة",
        "Vehicle Name": "اسم السيارة",
        "Rental Office": "مكتب التأجير",
        "Pricing Slab": "شريحة التسعير",
        "0-100 Ticket": "تذكرة 0-100",
        "Ticket 0-100": "تذكرة 0-100",
        "Reference Rate Card (Optional)": "كارت التسعير المرجعي (اختياري)",
        "Vehicle Type": "نوع السيارة",
        "0 - 100 KM Ticket Price": "سعر أول 100 كم",
        "Second Slab Upper KM": "الحد الأقصى للشريحة الثانية",
        "101 - Upper Slab Rate": "سعر الكيلو من 101 حتى الحد الأعلى",
        "Over Upper Slab Rate": "سعر الكيلو بعد الحد الأعلى",
        "Waiting Hour": "ساعة الانتظار",
        "Waiting Hour Rate": "سعر ساعة الانتظار",
        "Active Vehicle Rate": "تسعيرة سيارة نشطة",
        "Save Vehicle Rate": "حفظ تسعيرة السيارة",
        "Update Vehicle Rate": "تحديث تسعيرة السيارة",
        "Vehicle Rate List": "قائمة تسعير السيارات",
        "Upper Slab KM": "حد الشريحة العليا",
        "101-Upper Rate": "سعر 101 حتى الحد الأعلى",
        "Over Upper Rate": "سعر ما بعد الحد الأعلى",
        "Office Name": "اسم المكتب",
        "Rental Office List": "قائمة مكاتب التأجير",
        "Save Office": "حفظ المكتب",
        "Update Office": "تحديث المكتب",
        "Default Supplier Driver Name": "اسم سائق المورد الافتراضي",
        "Supplier Driver Name": "اسم سائق المورد",
        "Driver Source": "مصدر السائق",
        "Company Driver": "سائق من الشركة",
        "Supplier Driver": "سائق تابع للمورد",
        "Plate No": "رقم اللوحة",
        "Vehicle List": "قائمة السيارات",
        "Save Vehicle": "حفظ السيارة",
        "Update Vehicle": "تحديث السيارة",
        "Draft Setup": "إعداد المسودة",
        "Linked Work Orders": "أوامر الشغل المرتبطة",
        "Save Draft Trip": "حفظ مسودة الرحلة",
        "Update Draft Trip": "تحديث مسودة الرحلة",
        "Movement Manager Section": "جزء مدير الحركة",
        "Start Odometer": "عداد البداية",
        "Start Meter Photo": "صورة عداد البداية",
        "View Start Meter": "عرض عداد البداية",
        "No start photo yet.": "لا توجد صورة بداية بعد.",
        "End Odometer": "عداد النهاية",
        "End Meter Photo": "صورة عداد النهاية",
        "View End Meter": "عرض عداد النهاية",
        "No end photo yet.": "لا توجد صورة نهاية بعد.",
        "Waiting Hours": "ساعات الانتظار",
        "Movement Notes": "ملاحظات الحركة",
        "Save Start / Dispatch": "حفظ البداية / إرسال الرحلة",
        "Complete Trip": "إكمال الرحلة",
        "Accounting Approval": "اعتماد الحسابات",
        "Accounting Notes": "ملاحظات الحسابات",
        "Approve Trip": "اعتماد الرحلة",
        "Driver": "السائق",
        "KM": "كم",
        "Pending Accounting Approval": "بانتظار اعتماد الحسابات",
        "Pending approval": "بانتظار الاعتماد",
        "Please select the actual vehicle.": "من فضلك اختر السيارة الفعلية.",
        "Please select the company driver from HR employees.": "من فضلك اختر سائق الشركة من موظفي الموارد البشرية.",
        "Please enter the supplier driver name for this trip.": "من فضلك أدخل اسم سائق المورد لهذه الرحلة.",
        "Please select a rental office.": "من فضلك اختر مكتب التأجير.",
        "Please select the rental office for this pricing slab.": "من فضلك اختر مكتب التأجير لهذه الشريحة.",
        "Field maintenance, workshop repairs, cabinet assembly, and customer custody stock in one workflow.": "الصيانة الميدانية وإصلاحات الورشة وتجميع الكبائن ومخزون عهدة العميل في دورة تشغيل واحدة.",
        "Operational Flow": "دورة التشغيل",
        "Trip workflow is now live first: draft by technical manager, completion by movement manager, and final approval by accounting before transport cost is distributed.": "تم تشغيل دورة الرحلات أولاً: مسودة بواسطة مدير الفنيين، ثم استكمال بواسطة مدير الحركة، ثم اعتماد نهائي من الحسابات قبل توزيع تكلفة النقل.",
        "Field Maintenance": "الصيانة الميدانية",
        "Workshop Repairs": "إصلاحات الورشة",
        "Cabinet Assembly": "تجميع الكبائن",
        "Customer Custody": "عهدة العميل",
        "Master Data": "البيانات الأساسية",
        "Companies that open faults, send modules for repair, request cabinet assembly, or hand over custody stock.": "الشركات التي تفتح أعطالاً أو ترسل موديولات للإصلاح أو تطلب تجميع كبائن أو تسلم عهدة مخزون.",
        "Company Name": "اسم الشركة",
        "Contact Person": "الشخص المسؤول",
        "Active Company": "شركة نشطة",
        "Save Company": "حفظ الشركة",
        "Update Company": "تحديث الشركة",
        "Company List": "قائمة الشركات",
        "Service Category": "فئة الخدمة",
        "Active Fault": "عطل نشط",
        "Save Fault Type": "حفظ نوع العطل",
        "Update Fault Type": "تحديث نوع العطل",
        "Regions": "المناطق",
        "Area bands used for technician allowance and trip costing by destination.": "شرائح المناطق المستخدمة في بدل الفني وحساب تكلفة الرحلة حسب الوجهة.",
        "Region Name": "اسم المنطقة",
        "Zone Level": "مستوى المنطقة",
        "Allowance Amount": "قيمة البدل",
        "Active Region": "منطقة نشطة",
        "Save Region": "حفظ المنطقة",
        "Update Region": "تحديث المنطقة",
        "Region List": "قائمة المناطق",
        "Priced actions used in field maintenance, workshop repairs, and cabinet assembly. Each action can have a fixed list of raw materials.": "أكشنات مسعرة تستخدم في الصيانة الميدانية وإصلاحات الورشة وتجميع الكبائن، ويمكن لكل أكشن أن يحتوي على قائمة خامات ثابتة.",
        "Action Name": "اسم الأكشن",
        "Default Region Level": "مستوى المنطقة الافتراضي",
        "Default Duration (Hours)": "المدة الافتراضية (ساعات)",
        "Active Service": "أكشن نشط",
        "Save Action": "حفظ الأكشن",
        "Update Action": "تحديث الأكشن",
        "Use the template to import priced actions in bulk, then open each action and attach its fixed raw materials list.": "استخدم النموذج لاستيراد الأكشنات المسعرة دفعة واحدة، ثم افتح كل أكشن وأرفق قائمة الخامات الثابتة الخاصة به.",
        "Action List": "قائمة الأكشنات",
        "These are the fixed raw materials used to cost the work order automatically.": "هذه هي الخامات الثابتة المستخدمة في تسعير أمر الشغل تلقائيًا.",
        "Back to Action": "العودة إلى الأكشن",
        "Back to Catalog": "العودة إلى الدليل",
        "Action Price": "سعر الأكشن",
        "Fixed Material Cost": "تكلفة الخامات الثابتة",
        "Fixed Qty": "الكمية الثابتة",
        "Standard Unit Cost": "تكلفة الوحدة القياسية",
        "Add Fixed Material": "إضافة خامة ثابتة",
        "Fixed Raw Materials": "الخامات الثابتة",
        "Car rental suppliers or offices used for trip tickets. The same vehicle stays tied to one office.": "مكاتب أو شركات تأجير السيارات المستخدمة في تيكتات الرحلات. السيارة نفسها تظل مرتبطة بنفس المكتب.",
        "Active Rental Office": "مكتب تأجير نشط",
        "Each vehicle belongs to one rental office and one pricing slab. New trips automatically pick the latest active pricing slab for that office, type, and slab.": "كل سيارة مرتبطة بمكتب تأجير واحد وبشريحة تسعير واحدة. الرحلات الجديدة تسحب تلقائيًا آخر تسعيرة نشطة مطابقة للمكتب والنوع والشريحة.",
        "Active Vehicle": "سيارة نشطة",
        "Draft by technical manager, completion by movement manager, and accounting approval before transport cost hits work orders.": "يتم إعداد المسودة بواسطة مدير الفنيين، واستكمالها بواسطة مدير الحركة، واعتمادها من الحسابات قبل تحميل تكلفة النقل على أوامر الشغل.",
        "Back to Trips": "العودة إلى الرحلات",
        "Draft trip is prepared by the technical manager. Vehicle can still be changed while the trip is in draft only.": "يتم تجهيز مسودة الرحلة بواسطة مدير الفنيين، ويمكن تغيير السيارة فقط ما دامت الرحلة في حالة مسودة.",
        "One trip can serve more than one work order, and later the trip cost will be divided equally between them after accounting approval.": "يمكن لرحلة واحدة أن تخدم أكثر من أمر شغل، وبعد اعتماد الحسابات يتم توزيع تكلفة الرحلة عليهم بالتساوي.",
        "No work orders available yet. Create work orders first, then attach them to the trip.": "لا توجد أوامر شغل متاحة بعد. أنشئ أوامر الشغل أولاً ثم اربطها بالرحلة.",
        "Start and end odometer cannot be saved without the meter photo. Waiting hours are entered manually.": "لا يمكن حفظ عداد البداية أو النهاية بدون صورة العداد. ساعات الانتظار يتم إدخالها يدويًا.",
        "Saved": "محفوظ",
        "Missing": "غير موجود",
        "Trip Cost": "تكلفة الرحلة",
        "Driver Commission": "عمولة السائق",
        "Trip cost should only become visible on work orders after accounting approval.": "يجب ألا تظهر تكلفة الرحلة على أوامر الشغل إلا بعد اعتماد الحسابات.",
        "Only if the rental office provides the driver": "فقط إذا كان مكتب التأجير هو من يوفر السائق"
    };

    const patterns = [
        [/^Entries:\s*(.+)$/i, "القيود: $1"],
        [/^Debit:\s*(.+)$/i, "مدين: $1"],
        [/^Credit:\s*(.+)$/i, "دائن: $1"],
        [/^Companies:\s*(.+)$/i, "الشركات: $1"],
        [/^Contracts:\s*(.+)$/i, "العقود: $1"],
        [/^Tickets:\s*(.+)$/i, "التيكتات: $1"],
        [/^Fault Types:\s*(.+)$/i, "أنواع الأعطال: $1"],
        [/^Regions:\s*(.+)$/i, "المناطق: $1"],
        [/^Actions:\s*(.+)$/i, "الأكشنات: $1"],
        [/^Rental Offices:\s*(.+)$/i, "مكاتب التأجير: $1"],
        [/^Vehicles:\s*(.+)$/i, "السيارات: $1"],
        [/^Vehicle Rates:\s*(.+)$/i, "تسعير السيارات: $1"],
        [/^Trips:\s*(.+)$/i, "الرحلات: $1"],
        [/^Work Orders:\s*(.+)$/i, "أوامر الشغل: $1"],
        [/^Status:\s*(.+)$/i, "الحالة: $1"],
        [/^Trip No:\s*(.+)$/i, "رقم الرحلة: $1"],
        [/^Linked Work Orders:\s*(.+)$/i, "أوامر الشغل المرتبطة: $1"],
        [/^Total Cost:\s*(.+)$/i, "إجمالي التكلفة: $1"],
        [/^Start Photo:\s*(.+)$/i, "صورة البداية: $1"],
        [/^End Photo:\s*(.+)$/i, "صورة النهاية: $1"],
        [/^KM:\s*(.+)$/i, "كم: $1"],
        [/^Trip Cost:\s*(.+)$/i, "تكلفة الرحلة: $1"],
        [/^Driver Commission:\s*(.+)$/i, "عمولة السائق: $1"],
        [/^Per Work Order:\s*(.+)$/i, "لكل أمر شغل: $1"],
        [/^Journal Entry\s+(.+)$/i, "قيد يومية $1"],
        [/^Journal\s+(.+)$/i, "دفتر اليومية $1"],
        [/^Payroll\s+(.+)$/i, "مسير رواتب $1"],
        [/^Quotation\s+(.+)$/i, "عرض سعر $1"],
        [/^Sales Order\s+(.+)$/i, "أمر بيع $1"],
        [/^Delivery Note\s+(.+)$/i, "إذن تسليم $1"],
        [/^Vendor Bill\s+(.+)$/i, "فاتورة مورد $1"],
        [/^Customer Invoice\s+(.+)$/i, "فاتورة عميل $1"],
        [/^Fixed Asset Acquisition\s+(.+)$/i, "اقتناء أصل ثابت $1"],
        [/^Balance:\s*(.+)$/i, "الرصيد: $1"],
        [/^Paid Amount:\s*(.+)$/i, "المبلغ المدفوع: $1"],
        [/^Invoices:\s*(.+)$/i, "الفواتير: $1"],
        [/^Paid:\s*(.+)$/i, "مدفوع: $1"],
        [/^Partial:\s*(.+)$/i, "جزئي: $1"],
        [/^Total Qty:\s*(.+)$/i, "إجمالي الكمية: $1"],
        [/^PO-(.+)\s+approved by\s+(.+)\.$/i, "تم اعتماد أمر الشراء PO-$1 بواسطة $2."],
        [/^PO-(.+)\s+submitted by\s+(.+)\.$/i, "تم تقديم أمر الشراء PO-$1 بواسطة $2."],
        [/^PO-(.+)\s+created by\s+(.+)\. Submit it for approval\.$/i, "تم إنشاء أمر الشراء PO-$1 بواسطة $2. قم بإرساله للاعتماد."],
        [/^PO-(.+): accepted qty\s+(.+)\s+is ready for vendor billing\.$/i, "أمر الشراء PO-$1: الكمية المقبولة $2 جاهزة لفاتورة المورد."],
        [/^PO-(.+): short lines=(.+), over lines=(.+)\. Review PO Variances\.$/i, "أمر الشراء PO-$1: السطور الناقصة=$2 والزيادة=$3. راجع فروقات أمر الشراء."],
        [/^PO-(.+)\s+received in warehouse\. PO status:\s+(.+)\.$/i, "تم استلام أمر الشراء PO-$1 في المخزن. حالة أمر الشراء: $2."],
        [/^PO-(.+)\s+received and remaining qty was closed by warehouse decision\. PO status:\s+(.+)\.$/i, "تم استلام أمر الشراء PO-$1 وإغلاق الكمية المتبقية بقرار من المخزن. حالة أمر الشراء: $2."],
        [/^Warehouse Receipt Posted\s+\((.+)\)$/i, "تم ترحيل استلام المخزن ($1)"],
        [/^Import error:\s*(.+)$/i, "خطأ في الاستيراد: $1"],
        [/^Post error:\s*(.+)$/i, "خطأ في الترحيل: $1"],
        [/^Reverse error:\s*(.+)$/i, "خطأ في العكس: $1"],
        [/^No (.+) found\.$/i, "لا توجد بيانات."],
        [/^No (.+) found$/i, "لا توجد بيانات."]
    ];

    const phraseReplacements = [
        ["Entry no, description, reference...", "رقم القيد أو البيان أو المرجع..."],
        ["Search customer...", "ابحث عن عميل..."],
        ["Search vendor...", "ابحث عن مورد..."],
        ["Search warehouse...", "ابحث عن مخزن..."],
        ["Search item...", "ابحث عن صنف..."],
        ["Search PO...", "ابحث عن أمر شراء..."],
        ["Type 1 or 2 letters...", "اكتب حرف أو حرفين..."],
        ["No journal entries found for the selected filters.", "لا توجد قيود يومية مطابقة للفلاتر المحددة."],
        ["No attendance logs found.", "لا توجد سجلات حضور."],
        ["No employees found.", "لا يوجد موظفون."],
        ["No items found.", "لا توجد أصناف."],
        ["No categories found.", "لا توجد فئات."],
        ["No payroll runs found.", "لا توجد تشغيلات مرتبات."],
        ["No quotations found.", "لا توجد عروض أسعار."],
        ["No sales orders found.", "لا توجد أوامر بيع."],
        ["No delivery notes found.", "لا توجد أذون تسليم."],
        ["No records found.", "لا توجد سجلات."],
        ["No lines found.", "لا توجد سطور."],
        ["Customer master data", "بيانات العملاء الأساسية"],
        ["Vendor master data", "بيانات الموردين الأساسية"],
        ["Employee master data and import template", "بيانات الموظفين الأساسية وقالب الاستيراد"],
        ["Biometric attendance import and daily logs", "استيراد البصمة وسجلات الحضور اليومية"],
        ["Monthly payroll generation, review, and posting", "إعداد المرتبات الشهرية والمراجعة والترحيل"],
        ["Company and system initialization", "تهيئة الشركة والنظام"],
        ["Default accounts and prefixes", "الحسابات الافتراضية والبادئات"],
        ["Manage account structure", "إدارة هيكل الحسابات"],
        ["Department and activity allocation", "توزيع الأقسام والأنشطة"],
        ["Customer master and transactions", "البيانات الأساسية وحركات العملاء"],
        ["Vendor master and transactions", "البيانات الأساسية وحركات الموردين"],
        ["Journal entries and review", "قيود اليومية والمراجعة"],
        ["Operational expenses and posting", "المصروفات التشغيلية وترحيلها"],
        ["Custody and returns", "العهد والمرتجعات"],
        ["Assets, depreciation, and disposal", "الأصول والإهلاك والاستبعاد"],
        ["Financial and operational reports", "التقارير المالية والتشغيلية"],
        ["Warehouse structure and status", "هيكل المخازن وحالتها"],
        ["Receiving and stock intake", "الاستلام وإضافة المخزون"],
        ["Current stock by item and warehouse", "الرصيد الحالي حسب الصنف والمخزن"],
        ["Detailed inventory movement history", "التاريخ التفصيلي لحركة المخزون"],
        ["Purchase orders and follow-up", "أوامر الشراء والمتابعة"],
        ["Review quantity and price differences", "مراجعة فروقات الكميات والأسعار"],
        ["Price offers, negotiation, and pre-sale documents.", "عروض الأسعار والتفاوض ومستندات ما قبل البيع."],
        ["Confirmed customer demand ready for delivery or invoicing.", "طلبات العملاء المؤكدة الجاهزة للتسليم أو الفوترة."],
        ["Track goods handover before billing and operations follow-up.", "متابعة تسليم البضاعة قبل الفوترة والمتابعة التشغيلية."],
        ["Commercial billing linked with accounting and collections.", "فواتير البيع مرتبطة بالحسابات والتحصيل."],
        ["Track collections and allocate them to customer invoices.", "متابعة التحصيلات وتوزيعها على فواتير العملاء."],
        ["Open balances and movement history per customer.", "الأرصدة المفتوحة وحركة كل عميل."],
        ["A cleaner listing for due dates, amounts collected, outstanding balances, and fast actions.", "عرض أوضح لتواريخ الاستحقاق والمبالغ المحصلة والأرصدة القائمة والإجراءات السريعة."],
        ["Search by invoice number or customer, then narrow by date range and status.", "ابحث برقم الفاتورة أو العميل ثم ضيق النتائج بالتاريخ والحالة."],
        ["Link each employee to a category so attendance role, shift timing, grace minutes, and overtime policy can be applied automatically during attendance import and payroll processing.", "اربط كل موظف بفئة حتى يتم تطبيق دور الحضور والشيفت والدقائق المسموح بها وسياسة الإضافي تلقائيًا أثناء استيراد الحضور وتشغيل المرتبات."],
        ["Import exported attendance from the fingerprint device using employee code or biometric code. Payroll will use these logs to calculate worked days, overtime, and absence deduction.", "استورد ملف الحضور من جهاز البصمة باستخدام كود الموظف أو كود البصمة. سيستخدم نظام المرتبات هذه السجلات لحساب أيام العمل والإضافي وخصم الغياب."]
    ];

    function currentUiLang() {
        const params = new URLSearchParams(window.location.search);
        const queryLang = params.get("lang");
        if (queryLang === "ar" || queryLang === "en") {
            try { localStorage.setItem("ui_lang", queryLang); } catch (e) {}
            return queryLang;
        }
        try {
            return localStorage.getItem("ui_lang") === "ar" ? "ar" : "en";
        } catch (e) {
            return "en";
        }
    }

    function translateString(text) {
        if (!text) return text;
        const trimmed = text.trim();
        if (!trimmed) return text;

        if (Object.prototype.hasOwnProperty.call(exact, trimmed)) {
            return text.replace(trimmed, exact[trimmed]);
        }

        for (const [pattern, replacement] of patterns) {
            if (pattern.test(trimmed)) {
                return text.replace(trimmed, trimmed.replace(pattern, replacement));
            }
        }

        let output = text;
        for (const [en, ar] of phraseReplacements.sort((a, b) => b[0].length - a[0].length)) {
            if (output.includes(en)) {
                output = output.split(en).join(ar);
            }
        }

        return output;
    }

    function shouldSkipNode(node) {
        if (!node || !node.parentElement) return true;
        const tag = node.parentElement.tagName;
        return ["SCRIPT", "STYLE", "NOSCRIPT", "CODE", "PRE"].includes(tag);
    }

    function translateTextNodes(root) {
        if (!root) return;
        const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
        const nodes = [];
        while (walker.nextNode()) {
            const node = walker.currentNode;
            if (shouldSkipNode(node)) continue;
            const text = node.nodeValue;
            if (!text || !text.trim()) continue;
            nodes.push(node);
        }
        nodes.forEach((node) => {
            const translated = translateString(node.nodeValue);
            if (translated !== node.nodeValue) {
                node.nodeValue = translated;
            }
        });
    }

    function translateAttributes(root) {
        if (!root || !root.querySelectorAll) return;
        root.querySelectorAll("input, textarea, button, option").forEach((el) => {
            if (el.placeholder) {
                el.placeholder = translateString(el.placeholder);
            }
            if ((el.tagName === "INPUT" && ["button", "submit"].includes(el.type)) || el.tagName === "BUTTON") {
                if (el.value) el.value = translateString(el.value);
            }
            if (el.tagName === "OPTION" && el.textContent) {
                el.textContent = translateString(el.textContent);
            }
        });
    }

    function preserveLangOnLinks(lang) {
        if (lang !== "ar") return;
        document.querySelectorAll("a[href]").forEach((a) => {
            const href = a.getAttribute("href");
            if (!href || href.startsWith("#") || href.startsWith("javascript:") || href.startsWith("/static/")) return;
            if (href.startsWith("http")) return;
            try {
                const url = new URL(href, window.location.origin);
                if (url.pathname.startsWith("/static/")) return;
                url.searchParams.set("lang", "ar");
                a.setAttribute("href", url.pathname + url.search + url.hash);
            } catch (e) {
                // ignore invalid href
            }
        });

        document.querySelectorAll("form[action]").forEach((form) => {
            const action = form.getAttribute("action");
            if (!action || action.startsWith("http")) return;
            try {
                const url = new URL(action, window.location.origin);
                if (!url.searchParams.get("lang")) {
                    url.searchParams.set("lang", "ar");
                    form.setAttribute("action", url.pathname + url.search + url.hash);
                }
            } catch (e) {
                // ignore invalid action
            }
        });
    }

    function applyDirection(lang) {
        const isArabic = lang === "ar";
        document.documentElement.setAttribute("lang", isArabic ? "ar" : "en");
        document.documentElement.setAttribute("dir", isArabic ? "rtl" : "ltr");
        const toggleBtn = document.getElementById("langToggleBtn");
        if (toggleBtn) {
            toggleBtn.textContent = isArabic ? "English" : "عربي";
        }
    }

    let applyingI18n = false;
    let observerQueued = false;

    function applyTranslations(root) {
        if (applyingI18n) return;
        applyingI18n = true;
        try {
            translateAttributes(root || document.body);
            translateTextNodes(root || document.body);
        } finally {
            applyingI18n = false;
        }
    }

    function applyI18n() {
        const lang = currentUiLang();
        try { localStorage.setItem("ui_lang", lang); } catch (e) {}
        applyDirection(lang);
        preserveLangOnLinks(lang);
        if (lang !== "ar") return;
        applyTranslations(document.body);
    }

    window.applyI18n = applyI18n;
    window.currentUiLang = currentUiLang;

    document.addEventListener("DOMContentLoaded", function () {
        applyI18n();

        const observer = new MutationObserver(function (mutations) {
            if (currentUiLang() !== "ar" || applyingI18n || observerQueued) {
                return;
            }
            const roots = [];
            mutations.forEach(function (mutation) {
                mutation.addedNodes.forEach(function (node) {
                    if (node && node.nodeType === 1) {
                        roots.push(node);
                    } else if (node && node.parentElement) {
                        roots.push(node.parentElement);
                    }
                });
            });
            if (!roots.length) return;
            observerQueued = true;
            requestAnimationFrame(function () {
                try {
                    preserveLangOnLinks("ar");
                    roots.forEach(function (root) {
                        applyTranslations(root);
                    });
                } finally {
                    observerQueued = false;
                }
            });
        });
        observer.observe(document.body, { childList: true, subtree: true });
    });
})();


