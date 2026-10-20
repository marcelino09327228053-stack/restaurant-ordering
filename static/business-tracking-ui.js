(()=>{
'use strict';
const $=id=>document.getElementById(id);
const money=n=>new Intl.NumberFormat('en-PH',{style:'currency',currency:'PHP'}).format(Number(n)||0);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const apiBase='/api/business';
async function request(path,options={}){
 const key=typeof posTokenKey==='string'?posTokenKey:'owner_token';
 const token=localStorage.getItem(key);
 if(!token)throw Error('Owner login required.');
 const res=await fetch(apiBase+path,{...options,headers:{Authorization:'Bearer '+token,'Content-Type':'application/json',...(options.headers||{})}});
 const data=await res.json().catch(()=>({}));
 if(!res.ok)throw Error(typeof data.detail==='string'?data.detail:'Request failed (HTTP '+res.status+')');
 return data;
}
function notice(id,message,isError=false){const el=$(id);if(el){el.textContent=message;el.style.color=isError?'#fca5a5':'#86efac';}}
async function refreshInventory(){
 try{
  const [items,moves]=await Promise.all([request('/inventory'),request('/inventory/movements')]);
  $('inventoryItem').innerHTML=items.map(i=>`<option value="${i.id}">${esc(i.name)} (${esc(i.unit)})</option>`).join('');
  $('inventoryList').innerHTML=items.length?items.map(i=>`<tr><td>${esc(i.name)}</td><td>${esc(i.sku)}</td><td>${esc(i.quantity)} ${esc(i.unit)}</td><td>${esc(i.minimum_stock)}</td></tr>`).join(''):'<tr><td colspan="4">No inventory items yet.</td></tr>';
  $('movementList').innerHTML=moves.length?moves.map(m=>`<tr><td>${esc(m.created_at)}</td><td>${esc(m.item_name)}</td><td>${esc(m.movement_type)}</td><td>${esc(m.quantity)} ${esc(m.unit)}</td><td>${esc(m.note)}</td></tr>`).join(''):'<tr><td colspan="5">No stock movements yet.</td></tr>';
 }catch(e){notice('inventoryMessage',e.message,true);}
}
async function refreshExpenses(){
 try{
  const list=await request('/expenses');
  $('expenseTotal').textContent=money(list.reduce((n,e)=>n+Number(e.amount||0),0));
  $('expenseList').innerHTML=list.length?list.map(e=>`<tr><td>${esc(e.expense_date)}</td><td>${esc(e.category)}</td><td>${esc(e.description)}</td><td>${money(e.amount)}</td><td>${esc(e.recorded_by)}</td></tr>`).join(''):'<tr><td colspan="5">No expenses recorded yet.</td></tr>';
 }catch(e){notice('expenseMessage',e.message,true);}
}
const style=`<style>.tracking-form{display:flex;flex-wrap:wrap;gap:10px;margin:12px 0 20px}.tracking-form input,.tracking-form select{background:#121217;color:#fff;border:1px solid #41414a;border-radius:9px;padding:10px;min-width:130px;flex:1}.tracking-form button{background:#f97316;color:white;border:0;border-radius:9px;padding:10px 18px;font-weight:800;cursor:pointer}.tracking-table{width:100%;border-collapse:collapse;margin:10px 0 24px}.tracking-table td,.tracking-table th{padding:10px;text-align:left;border-bottom:1px solid #34343a}.tracking-table th{color:#fdba74}.tracking-scroll{overflow:auto}.tracking-title{margin-top:24px;color:#fdba74}</style>`;
function setup(){
 const inventory=$('inventoryWorkspace'),expenses=$('expensesWorkspace');
 if(!inventory||!expenses)return;
 inventory.innerHTML=style+`<h3 class="tracking-title">Add Inventory Item</h3><form class="tracking-form" id="addItemForm"><input name="name" placeholder="Item / material name" maxlength="180" required><input name="sku" placeholder="SKU (optional)" maxlength="100"><input name="unit" placeholder="Unit (pcs, kg, liter)" value="pcs" required><input name="minimum_stock" type="number" step="0.001" min="0" placeholder="Minimum stock" value="0" required><button>Add Item</button></form><h3 class="tracking-title">Stock Movement</h3><form class="tracking-form" id="movementForm"><select id="inventoryItem" name="item_id" required></select><select name="movement_type"><option value="stock_in">Stock In</option><option value="stock_out">Stock Out</option><option value="used">Materials Used</option></select><input name="quantity" type="number" min="0.001" step="0.001" placeholder="Quantity" required><input name="note" placeholder="Reason / reference"><button>Save Movement</button></form><p id="inventoryMessage" role="status"></p><h3 class="tracking-title">Current Stock</h3><div class="tracking-scroll"><table class="tracking-table"><thead><tr><th>Item</th><th>SKU</th><th>Remaining</th><th>Min Stock</th></tr></thead><tbody id="inventoryList"></tbody></table></div><h3 class="tracking-title">Movement History (latest 500)</h3><div class="tracking-scroll"><table class="tracking-table"><thead><tr><th>Date</th><th>Item</th><th>Type</th><th>Quantity</th><th>Note</th></tr></thead><tbody id="movementList"></tbody></table></div>`;
 expenses.innerHTML=style+`<h3 class="tracking-title">Record Business Expense</h3><form class="tracking-form" id="expenseForm"><input name="category" placeholder="Category (supplies, rent, bills)" maxlength="100" required><input name="description" placeholder="Description / what was purchased" maxlength="1000"><input name="amount" type="number" step="0.01" min="0.01" placeholder="Amount (PHP)" required><input name="expense_date" type="date" required><button>Save Expense</button></form><p id="expenseMessage" role="status"></p><h3>Total recorded (latest 500): <span id="expenseTotal">₱0.00</span></h3><div class="tracking-scroll"><table class="tracking-table"><thead><tr><th>Date</th><th>Category</th><th>Description</th><th>Amount</th><th>Recorded By</th></tr></thead><tbody id="expenseList"></tbody></table></div>`;
 $('expenseForm').elements.expense_date.value=new Date().toLocaleDateString('en-CA');
 for(const [formId,path,messageId,refresh] of [['addItemForm','/inventory','inventoryMessage',refreshInventory],['movementForm','/inventory/movements','inventoryMessage',refreshInventory],['expenseForm','/expenses','expenseMessage',refreshExpenses]]){
  $(formId).addEventListener('submit',async e=>{e.preventDefault();const form=e.currentTarget;const data=Object.fromEntries(new FormData(form));const btn=form.querySelector('button');btn.disabled=true;try{await request(path,{method:'POST',body:JSON.stringify(data)});notice(messageId,'Saved successfully.');if(formId!=='addItemForm')form.reset();if(formId==='expenseForm')form.elements.expense_date.value=new Date().toLocaleDateString('en-CA');await refresh();}catch(err){notice(messageId,err.message,true);}finally{btn.disabled=false;}});
 }
 window.loadBusinessInventory=refreshInventory;
 window.loadBusinessExpenses=refreshExpenses;
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',setup);else setup();
})();
