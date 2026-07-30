"""API routes for customer ordering and cashier board."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app import repository as repo
from app.auth import create_access_token, require_cashier

router = APIRouter(prefix="/api", tags=["restaurant"])


class LoginRequest(BaseModel):
    password: str = Field(min_length=1, max_length=200)


class OrderItemCreate(BaseModel):
    menu_item_id: int = Field(gt=0)
    quantity: int = Field(ge=1, le=50)


class OrderCreate(BaseModel):
    items: list[OrderItemCreate] = Field(min_length=1, max_length=50)
    customer_note: str = Field(default="", max_length=500)


class StatusUpdate(BaseModel):
    status: str


class MenuItemCreate(BaseModel):
    category: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=500)
    price: float = Field(gt=0, le=1_000_000)


class AvailabilityUpdate(BaseModel):
    available: bool


class TableCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)


@router.post("/login")
def login(body: LoginRequest):
    if not repo.authenticate_cashier(body.password):
        raise HTTPException(status_code=401, detail="Incorrect cashier password.")
    return {"token": create_access_token(), "restaurant": repo.get_settings()}


@router.get("/public/{access_code}/menu")
def public_menu(access_code: str):
    table = repo.get_public_table(access_code)
    if table is None:
        raise HTTPException(status_code=404, detail="Invalid or inactive table QR code.")
    return {
        "restaurant_name": table["restaurant_name"],
        "table_name": table["name"],
        "items": repo.list_menu(available_only=True),
    }


@router.post("/public/{access_code}/orders", status_code=201)
def place_order(access_code: str, body: OrderCreate):
    table = repo.get_public_table(access_code)
    if table is None:
        raise HTTPException(status_code=404, detail="Invalid or inactive table QR code.")
    try:
        return repo.create_order(
            table,
            [item.model_dump() for item in body.items],
            body.customer_note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/public/{access_code}/orders/{order_number}")
def public_order_status(access_code: str, order_number: str):
    order = repo.get_public_order(access_code, order_number)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found.")
    return order


@router.get("/orders")
def cashier_orders(status: str | None = None, _=Depends(require_cashier)):
    if status and status not in repo.ORDER_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid order status.")
    return repo.list_orders(status)


@router.patch("/orders/{order_id}/status")
def change_order_status(
    order_id: int, body: StatusUpdate, _=Depends(require_cashier)
):
    if body.status not in repo.ORDER_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid order status.")
    order, error = repo.update_order_status(order_id, body.status)
    if error == "not_found":
        raise HTTPException(status_code=404, detail="Order not found.")
    if error == "invalid_transition":
        raise HTTPException(
            status_code=409,
            detail=f"Cannot change order from {order['status']} to {body.status}.",
        )
    return order


@router.get("/menu")
def manage_menu(_=Depends(require_cashier)):
    return repo.list_menu()


@router.post("/menu", status_code=201)
def add_menu_item(body: MenuItemCreate, _=Depends(require_cashier)):
    item = repo.create_menu_item(
        body.category, body.name, body.description, body.price
    )
    if item is None:
        raise HTTPException(status_code=409, detail="A menu item with that name already exists.")
    return item


@router.patch("/menu/{item_id}/availability")
def change_availability(
    item_id: int, body: AvailabilityUpdate, _=Depends(require_cashier)
):
    item = repo.set_menu_item_availability(item_id, body.available)
    if item is None:
        raise HTTPException(status_code=404, detail="Menu item not found.")
    return item


@router.get("/tables")
def manage_tables(_=Depends(require_cashier)):
    return repo.list_tables()


@router.post("/tables", status_code=201)
def add_table(body: TableCreate, _=Depends(require_cashier)):
    table = repo.create_table(body.name)
    if table is None:
        raise HTTPException(status_code=409, detail="A table with that name already exists.")
    return table
