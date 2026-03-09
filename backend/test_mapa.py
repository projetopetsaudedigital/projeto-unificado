import urllib.request
import json

req = urllib.request.Request(
    'http://localhost:8000/api/v1/auth/login', 
    data=json.dumps({"email":"admin@plataforma.saude","senha":"admin123"}).encode(), 
    headers={'Content-Type':'application/json'}
)
res = urllib.request.urlopen(req)
token = json.loads(res.read())['access_token']

req_mapa = urllib.request.Request(
    'http://localhost:8000/api/v1/pressao-arterial/mapa',
    headers={'Authorization': f'Bearer {token}'}
)
res_mapa = urllib.request.urlopen(req_mapa)
d = json.loads(res_mapa.read())
print(f"Mapa retornou {len(d.get('bairros', []))} bairros geocodificados!")
