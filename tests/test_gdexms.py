# test_gdexms.py

def test_import():
   import gdex_python_gdexms
   assert gdex_python_gdexms.__version__


def test_healthz():
   from gdex_python_gdexms.app import create_app
   client = create_app({"TESTING": True}).test_client()
   resp = client.get("/healthz")
   assert resp.status_code == 200
   assert resp.get_json()["status"] == "ok"
