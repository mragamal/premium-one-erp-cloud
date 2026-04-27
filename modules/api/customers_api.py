from fastapi import APIRouter, HTTPException
import sqlite3

router = APIRouter(prefix="/api/customers", tags=["Customers API"])


def get_db():
    return sqlite3.connect("erp.db")


# 🔹 GET ALL CUSTOMERS
@router.get("/")
def get_customers():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id, name, phone FROM customers")
    rows = cursor.fetchall()

    conn.close()

    return [
        {"id": r[0], "name": r[1], "phone": r[2]}
        for r in rows
    ]


# 🔹 ADD CUSTOMER
@router.post("/")
def add_customer(data: dict):
    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO customers (name, phone) VALUES (?, ?)",
            (data.get("name"), data.get("phone"))
        )
        conn.commit()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()

    return {"message": "Customer added successfully"}


# 🔹 UPDATE CUSTOMER
@router.put("/{customer_id}")
def update_customer(customer_id: int, data: dict):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE customers SET name=?, phone=? WHERE id=?",
        (data.get("name"), data.get("phone"), customer_id)
    )

    conn.commit()
    conn.close()

    return {"message": "Customer updated"}


# 🔹 DELETE CUSTOMER
@router.delete("/{customer_id}")
def delete_customer(customer_id: int):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM customers WHERE id=?", (customer_id,))
    conn.commit()
    conn.close()

    return {"message": "Customer deleted"}