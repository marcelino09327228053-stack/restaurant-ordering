"""Owner-scoped inventory and expenses API."""
from datetime import date
from decimal import Decimal, InvalidOperation
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from app.auth import require_owner
from app.db import get_connection

router = APIRouter(prefix="/api/business", tags=["business-tracking"])

class ItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    sku: str = Field(default="", max_length=100)
    unit: str = Field(default="pcs", min_length=1, max_length=30)
    minimum_stock: Decimal = Field(default=Decimal("0"), ge=0)

class MovementCreate(BaseModel):
    item_id: int
    movement_type: str
    quantity: Decimal = Field(gt=0)
    note: str = Field(default="", max_length=1000)

class ExpenseCreate(BaseModel):
    category: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=1000)
    amount: Decimal = Field(gt=0)
    expense_date: date

def rows(cursor):
    return [dict(row) for row in cursor.fetchall()]

@router.get("/inventory")
def list_inventory(actor=Depends(require_owner)):
    cur=get_connection().cursor()
    cur.execute("SELECT * FROM inventory_items WHERE owner_id=? AND active=1 ORDER BY name,id",(actor["owner_id"],))
    return rows(cur)

@router.post("/inventory")
def add_inventory_item(body:ItemCreate,actor=Depends(require_owner)):
    conn=get_connection();cur=conn.cursor()
    cur.execute("INSERT INTO inventory_items(owner_id,name,sku,unit,minimum_stock) VALUES(?,?,?,?,?)",(actor["owner_id"],body.name.strip(),body.sku.strip(),body.unit.strip(),str(body.minimum_stock)))
    conn.commit()
    return {"id":cur.lastrowid,"message":"Inventory item created"}

@router.get("/inventory/movements")
def list_movements(actor=Depends(require_owner)):
    cur=get_connection().cursor()
    cur.execute("SELECT m.*,i.name AS item_name,i.unit FROM inventory_movements m JOIN inventory_items i ON i.id=m.item_id WHERE m.owner_id=? ORDER BY m.id DESC LIMIT 500",(actor["owner_id"],))
    return rows(cur)

@router.post("/inventory/movements")
def add_movement(body:MovementCreate,actor=Depends(require_owner)):
    if body.movement_type not in ("stock_in","stock_out","used"):
        raise HTTPException(400,"Invalid movement type")
    qty=body.quantity.quantize(Decimal("0.001"))
    if qty<=0:raise HTTPException(400,"Quantity must be at least 0.001")
    conn=get_connection();cur=conn.cursor()
    try:
        if hasattr(conn,"execute"):conn.execute("BEGIN IMMEDIATE")
        cur.execute("SELECT quantity FROM inventory_items WHERE id=? AND owner_id=? AND active=1",(body.item_id,actor["owner_id"]))
        item=cur.fetchone()
        if not item:raise HTTPException(404,"Inventory item not found")
        current=Decimal(str(item["quantity"]))
        new=current+qty if body.movement_type=="stock_in" else current-qty
        if new<0:raise HTTPException(400,"Insufficient stock")
        cur.execute("UPDATE inventory_items SET quantity=? WHERE id=? AND owner_id=?",(str(new),body.item_id,actor["owner_id"]))
        cur.execute("INSERT INTO inventory_movements(owner_id,item_id,movement_type,quantity,note,recorded_by) VALUES(?,?,?,?,?,?)",(actor["owner_id"],body.item_id,body.movement_type,str(qty),body.note.strip(),actor.get("email","owner")))
        conn.commit()
        return {"remaining_quantity":str(new),"message":"Stock movement recorded"}
    except Exception:
        conn.rollback()
        raise

@router.get("/expenses")
def list_expenses(actor=Depends(require_owner)):
    cur=get_connection().cursor()
    cur.execute("SELECT * FROM business_expenses WHERE owner_id=? ORDER BY expense_date DESC,id DESC LIMIT 500",(actor["owner_id"],))
    return rows(cur)

@router.post("/expenses")
def add_expense(body:ExpenseCreate,actor=Depends(require_owner)):
    amount=body.amount.quantize(Decimal("0.01"))
    if amount<=0:raise HTTPException(400,"Amount must be at least 0.01")
    conn=get_connection();cur=conn.cursor()
    cur.execute("INSERT INTO business_expenses(owner_id,category,description,amount,expense_date,recorded_by) VALUES(?,?,?,?,?,?)",(actor["owner_id"],body.category.strip(),body.description.strip(),str(amount),body.expense_date.isoformat(),actor.get("email","owner")))
    conn.commit()
    return {"id":cur.lastrowid,"message":"Expense recorded"}
