import os, tempfile, sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
folder=tempfile.mkdtemp(prefix='restaurant-menu-editor-')
os.environ['DATABASE_URL']=''
os.environ['SQLITE_PATH']=str(Path(folder)/'test.db')
os.environ['CLOUDINARY_URL']=''
os.environ['CLOUDINARY_CLOUD_NAME']=''
from app.main import app
import app.router as api_routes
from starlette.routing import Mount
from starlette.staticfiles import StaticFiles
artifacts = Path(tempfile.gettempdir()) / 'restaurant-menu-editor-check'
artifacts.mkdir(exist_ok=True)
api_routes.UPLOAD_ROOT = Path(folder) / 'uploads'
api_routes.UPLOAD_ROOT.mkdir()
app.router.routes.insert(0, Mount('/static/uploads', app=StaticFiles(directory=str(api_routes.UPLOAD_ROOT))))
from app.db import get_connection
from app import repository as repo
from app.auth import create_owner_token, create_access_token
conn=get_connection()
owner_id=conn.execute("INSERT INTO owners(email,restaurant_name,slug) VALUES ('editor-test@example.test','Editor Test','editor-test')").lastrowid
conn.commit()
repo.update_owner_site(owner_id,custom_design={'editorDraft':{'objects':[]},'sentinel':'preserve'})
repo.create_owner_menu_item(owner_id,'Meals','Test meal','Test description',125)
table=repo.create_owner_table(owner_id,'Editor Test Table')
import json
(artifacts / 'session.json').write_text(json.dumps({'token':create_owner_token(owner_id,'editor-test@example.test'),'cashier':create_access_token(),'table':table['access_code']}))
import uvicorn
uvicorn.run(app,host='127.0.0.1',port=8011)
