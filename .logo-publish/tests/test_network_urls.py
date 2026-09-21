import os, sys, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.network import connection_info, table_order_url, room_join_url
class NetworkURLs(unittest.TestCase):
    def test_render(self):
        with patch.dict(os.environ,{"PUBLIC_BASE_URL":"", "RENDER_EXTERNAL_URL":"https://restaurant.example", "PORT":"10000"}), patch("app.network.preferred_lan_ip", side_effect=AssertionError("No LAN detection on Render")):
            self.assertEqual(table_order_url("abc"),"https://restaurant.example/order?table=abc")
            self.assertEqual(room_join_url("abc"),"https://restaurant.example/join/abc")
            self.assertFalse(connection_info()["offline_ready"])
    def test_explicit_base(self):
        with patch.dict(os.environ,{"PUBLIC_BASE_URL":"https://custom.example/", "RENDER_EXTERNAL_URL":"https://render.example"}):
            self.assertEqual(connection_info()["base_url"],"https://custom.example")
    def test_local(self):
        with patch.dict(os.environ,{"PUBLIC_BASE_URL":"", "RENDER_EXTERNAL_URL":"", "LAN_IP":"192.168.1.5", "PORT":"8010"}):
            self.assertEqual(table_order_url("abc"),"http://192.168.1.5:8010/order?table=abc")
            self.assertTrue(connection_info()["offline_ready"])
if __name__ == "__main__": unittest.main()
