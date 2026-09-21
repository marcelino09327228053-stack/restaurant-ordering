"""Run in an isolated process: python tests/test_table_billing.py."""
import os
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
_tmp = tempfile.TemporaryDirectory()
os.environ["DATABASE_URL"] = ""
os.environ["SQLITE_PATH"] = str(Path(_tmp.name) / "test.db")
from app.db import init_db, get_connection
from app import repository as repo
init_db()
repo.ensure_defaults()
conn = get_connection()
c = conn.cursor()
table_id = c.execute("SELECT id FROM restaurant_tables LIMIT 1").fetchone()[0]
for i in range(5):
    c.execute("INSERT INTO restaurant_orders(table_id,order_number,total,status) VALUES (?,?,200,'served')", (table_id, f"TEST-{i}"))
conn.commit()
ids = [r[0] for r in c.execute("SELECT id FROM restaurant_orders").fetchall()]
assert repo.list_table_bills()[0]["total"] == 1000
assert repo.close_table_bill(table_id, ids)["closed_orders"] == 0
assert repo.settle_table_orders(table_id, ids[:1])["amount_recorded"] == 200
assert repo.settle_table_orders(table_id, ids[1:2])["amount_recorded"] == 200
bill = repo.list_table_bills()[0]
assert (bill["total"],bill["paid"],bill["balance"]) == (1000,400,600)
assert repo.settle_table_orders(table_id, ids[:2])["amount_recorded"] == 0
assert repo.settle_table_orders(table_id+999, ids)["amount_recorded"] == 0
assert repo.settle_table_orders(table_id, ids)["amount_recorded"] == 600
assert repo.list_table_bills()[0]["balance"] == 0
repo.set_order_payment_proof(ids[0],"/late-proof.png")
repo.update_payment_status(ids[0],"rejected")
assert repo.get_order_by_id(ids[0])["payment_status"] == "verified"
# New orders must survive closing the previous displayed bill.
c.execute("INSERT INTO restaurant_orders(table_id,order_number,total,status) VALUES (?, 'NEXT', 150, 'pending')",(table_id,))
conn.commit()
assert repo.close_table_bill(table_id, ids)["closed_orders"] == 5
assert repo.close_table_bill(table_id, ids)["closed_orders"] == 0
assert repo.list_table_bills()[0]["balance"] == 150
print("PASS: split, combined, balances, retries, wrong table, late proof, closing and next party")
# Exercise authenticated routes over a real local HTTP server, without external dependencies.
import threading, socket, json, urllib.request, urllib.error
import uvicorn
from fastapi import FastAPI
from app.router import router
from app.auth import create_access_token
app = FastAPI(); app.include_router(router)
sock = socket.socket(); sock.bind(("127.0.0.1",0)); port=sock.getsockname()[1]
server=uvicorn.Server(uvicorn.Config(app,log_level="error"))
thread=threading.Thread(target=lambda:server.run(sockets=[sock]),daemon=True);thread.start()
import time
for _ in range(100):
    if server.started: break
    time.sleep(.05)
base=f"http://127.0.0.1:{port}/api/table-bills"
try:
    try: urllib.request.urlopen(base); raise AssertionError("Unauthenticated access")
    except urllib.error.HTTPError as e: assert e.code==401
    headers={"Authorization":"Bearer "+create_access_token(),"Content-Type":"application/json"}
    with urllib.request.urlopen(urllib.request.Request(base,headers=headers)) as r:
        bills=json.load(r); assert bills[0]["balance"]==150
    new_id=bills[0]["orders"][0]["id"]
    req=urllib.request.Request(base+f"/{table_id}/pay",data=json.dumps({"order_ids":[new_id]}).encode(),headers=headers)
    with urllib.request.urlopen(req) as r: assert json.load(r)["amount_recorded"]==150
    print("PASS: local HTTP authentication, bill listing, payment route")
finally:
    server.should_exit=True;thread.join(5);sock.close();conn.close();_tmp.cleanup()
