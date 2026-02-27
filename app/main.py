import httpx
import asyncio
import os
import json
from dotenv import load_dotenv

from fastapi import FastAPI, status, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse

import simplekml

app: FastAPI = FastAPI(title="Service Order Orchstrator")
app.mount("/static", StaticFiles(directory="static"), name="static")

load_dotenv()

VIGO_URL = os.getenv("VIGO_BASE_URL")
TOKEN = os.getenv("TOKEN")

http_client = httpx.AsyncClient(limits=httpx.Limits(max_keepalive_connections=50, max_connections=100))

@app.get("/", response_class=HTMLResponse)
async def index():
    with open("static/index.html", "r") as f:
        return f.read()

@app.get("/order/{order_id}", status_code=status.HTTP_200_OK)
async def fetch_order_details(order_id: str, base_url: str = VIGO_URL, token: str = TOKEN):
    if not base_url or not token:
        print("Error: Missing VIGO_BASE_URL or TOKEN in environment.")
        raise HTTPException(status_code=502, detail="VIGO API is unreachable or returned an error.") 

    url_order = f"{base_url}/api/app_getcustom"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    payload = {
        "campo1": "id",
        "campo1_valor": str(order_id),
        "campo2": "none",
        "campo2_valor": "none"
    }

    try:
        response = await http_client.post(url_order, json=payload, headers=headers)
        
        if response.status_code == 200:
            list_data = response.json()
            if not list_data or not isinstance(list_data, list):
                print("API returned empty or invalid data format.")
                raise HTTPException(status_code=502, detail="API returned empty or invalid data format.")
            dict_data = list_data[0]

            formated_data = {
                "cli_id":dict_data["id_cliente"],
                "cli_name":dict_data["nome"],
                "cli_login":None,
                "cli_pass":None,
                "cli_panel":None,
                "cli_loc":dict_data["anotacao_tecnica"],
                "cli_address":None,
                "order_desc":dict_data["historico"]
            }

            return formated_data
        else:
            print(f"API Error: {response.status_code} - {response.text}")
            raise HTTPException(status_code=502, detail=f"API Error: {response.status_code} - {response.text}")
            
    except httpx.RequestError as exc:
        print(f"Connection error: {exc.request.url!r}")
        raise HTTPException(status_code=502, detail=f"Connection error: {exc.request.url!r}")

@app.get("/client/{cli_id}", status_code=status.HTTP_200_OK)
async def fetch_client_data(cli_id: str, base_url: str = VIGO_URL, token: str = TOKEN):
    if not base_url or not token:
        print("Error: Missing VIGO_BASE_URL or TOKEN in environment.")
        raise HTTPException(status_code=502, detail="VIGO API is unreachable or returned an error.")
    
    cli_url = f"{base_url}/api/app_getcliente"

    headers = {
        "Content-Type": "application/json", 
        "Authorization": f"Bearer {token}"
    }

    payload = {
        "campo1": "ID",
        "campo1_valor": str(cli_id),
        "campo2": "none",
        "campo2_valor": "none"
    }

    try:
        response = await http_client.post(cli_url, json=payload, headers=headers)

        if response.status_code==200:
            data =  response.json()

            if data.get("situacao") == "L":
                return data
            
            raise HTTPException(status_code=403, detail=f"Client {cli_id} is not 'L'. Current status: {data.get('situacao')}")
        else:
            print(f"API Error: {response.status_code} - {response.text}")
            raise HTTPException(status_code=502, detail=f"API Error: {response.status_code} - {response.text}")
    except httpx.RequestError as exc:
        print(f"Connection error: {exc.request.url!r}")
        raise HTTPException(status_code=502, detail=f"Connection error: {exc.request.url!r}")
        
@app.get("/marker_create/{order_id}")
async def marker_create(order_id: str):
    order_data = await fetch_order_details(order_id, VIGO_URL, TOKEN)
    client_data = await fetch_client_data(order_data['cli_id'], VIGO_URL, TOKEN)
    lon = client_data.get('longitude')
    lat = client_data.get('latitude')
    if not lon or not lat:
        print(f"Error: Missing coordinates for client {order_data.get('cli_id')}")
        raise HTTPException(status_code=422, detail="Missing coordinates.")
        
    clean_description = order_data['order_desc'].replace('\r\n', '<br>').replace('\n', '<br>')

    print("################ order_data ################")
    print(f"Longitude = {client_data['longitude']}, Latitude = {client_data['latitude']}")
    print(json.dumps(order_data, indent=4))

    kml = simplekml.Kml()
    kml.newpoint(
        name=f"{order_data['cli_id']} - {order_data['cli_name']}", 
        coords=[(lon, lat)], 
        description=(
            f"SUPORTE A SER REALIZADO<br><br>"
            f"{order_data['cli_id']} - {order_data['cli_name']}<br><br>"
            f"LOGIN: {order_data['cli_login']}<br>"
            f"SENHA: {order_data['cli_pass']}<br>"
            f"PAINEL: {order_data['cli_panel']}<br><br>"
            f"Localização: {order_data['cli_loc']}<br>"
            f"Endereço: {order_data['cli_address']}<br><br>"
            f"Solucionar:<br>{clean_description}"
        )
    )

    filename = f"order_{order_id}_MAP.kml"
    kml.save(filename)
    
    if os.path.exists(filename):
        return FileResponse(path=filename, filename=filename, media_type='application/vnd.google-earth.kml+xml')
    raise HTTPException(status_code=500, detail="File generation failed")

@app.get("/get_open_order/")
async def fetch_order_by_filter(campo1: str = "h_fechamento", valor1: str = "", cidade: str = "Catalão", tipo: str = "Suporte (rádio/fibra)"):
    print(f"DEBUG: Recebido no Python -> Cidade: '{cidade}' | Tipo: '{tipo}'")
    url = f"{VIGO_URL}/api/app_getcustom"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {TOKEN}"
    }

    payload = {
        "campo1": campo1,
        "campo1_valor": valor1,
        "campo2": None,
        "campo2_valor": None
    }

    try:
        response = await http_client.post(url, json=payload, headers=headers)
        
        if response.status_code == 200:
            list_opened_order = response.json()

            city_order = [
                {
                "cli_id":order["id_cliente"],
                "cli_name":order["nome"],
                "cli_login":None,
                "cli_pass":None,
                "cli_panel":None,
                "Tipo":order["desc_tatendimento"],
                "cli_loc":order["anotacao_tecnica"],
                "cli_address":None,
                "order_desc":order["historico"]
            } for order in list_opened_order if order['cidade'] == cidade and order['desc_tatendimento'] == tipo
            ]
            
            return city_order
        else:
            print(f"Erro na API: {response.status_code} - {response.text}")
            raise HTTPException(status_code=502, detail=f"Erro na API: {response.status_code}")
    except httpx.RequestError as exc:
        print(f"Erro de conexão ao buscar filtros: {exc}")
        raise HTTPException(status_code=502, detail="Erro de conexão ao buscar filtros")
        
@app.get("/list_marker_create/")
async def create_marker_list(cidade: str = "Catalão", tipo: str = "Suporte (rádio/fibra)"):
    CITY_MAP = {
        "catalao": "Catalão",
        "ouvidor": "Ouvidor",
        "davinopolis": "Davinópolis"
    }

    TYPE_MAP = {
        "suporte": "Suporte (rádio/fibra)",
        "rural": "Suporte Rural",
        "retirada": "Retirada"
    }
    
    cidade_real = CITY_MAP.get(cidade, "Catalão")
    tipo_real = TYPE_MAP.get(tipo, "Suporte (rádio/fibra)")

    order_list = await fetch_order_by_filter(cidade=cidade_real, tipo=tipo_real)
    print(order_list)
    kml = simplekml.Kml()

    for order in order_list:
        try:
            client_data = await fetch_client_data(order['cli_id'], VIGO_URL, TOKEN)
            if not client_data:
                continue
            lon = client_data.get('longitude')
            lat = client_data.get('latitude')
            
            if not lon or not lat or str(lon) == "0" or str(lat) == "0":
                print(f"CLient without coords {order.get('cli_id')}: setted in default place")
                lon = "-47.94679761674606"
                lat = "-18.158900260837715"

            clean_description = order['order_desc'].replace('\r\n', '<br>').replace('\n', '<br>')

            kml.newpoint(
                name=f"{order['cli_id']} - {order['cli_name']}", 
                coords=[(lon, lat)], 
                description=(
                    f"SUPORTE A SER REALIZADO<br><br>"
                    f"{order['cli_id']} - {order['cli_name']}<br><br>"
                    f"LOGIN: {order['cli_login']}<br>"
                    f"SENHA: {order['cli_pass']}<br>"
                    f"PAINEL: {order['cli_panel']}<br><br>"
                    f"Localização: {order['cli_loc']}<br>"
                    f"Endereço: {order['cli_address']}<br><br>"
                    f"Solucionar:<br>{clean_description}"
                )
            )
        except HTTPException:
            continue

    filename = "order_MAP_GLOBAL.kml"
    kml.save(filename)

    if os.path.exists(filename):
        return FileResponse(path=filename, filename=filename, media_type='application/vnd.google-earth.kml+xml')
    raise HTTPException(status_code=500, detail="File generation failed")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)