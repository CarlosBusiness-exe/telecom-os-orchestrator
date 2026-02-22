import httpx
import asyncio
import os
import json
from dotenv import load_dotenv

from fastapi import FastAPI
from fastapi import status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import  FileResponse, HTMLResponse

import simplekml

app: FastAPI = FastAPI(title="OS Orchstrator")
app.mount("/static", StaticFiles(directory="static"), name="static")

load_dotenv()

VIGO_URL = os.getenv("VIGO_BASE_URL")
TOKEN = os.getenv("TOKEN")

@app.get("/", response_class=HTMLResponse)
async def index():
    with open("static/index.html", "r") as f:
        return f.read()

@app.get("/os/{os_id}", status_code=status.HTTP_200_OK)
async def fetch_os_details(os_id: str, base_url: str = VIGO_URL, token: str = TOKEN):
    if not base_url or not token:
        print("Error: Missing VIGO_BASE_URL or TOKEN in environment.")
        return None

    url_os = f"{base_url}/api/app_getcustom"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    payload = {
        "campo1": "id",
        "campo1_valor": str(os_id),
        "campo2": "none",
        "campo2_valor": "none"
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url_os, json=payload, headers=headers)
            
            if response.status_code == 200:
                list_data = response.json()
                if not list_data or not isinstance(list_data, list):
                    print("API returned empty or invalid data format.")
                    return None
                dict_data = list_data[0]

                formated_data = {
                    "cli_id":dict_data["id_cliente"],
                    "cli_name":dict_data["nome"],
                    "cli_login":None,
                    "cli_pass":None,
                    "cli_panel":None,
                    "cli_loc":dict_data["anotacao_tecnica"],
                    "cli_address":None,
                    "os_desc":dict_data["historico"]
                }

                #print("################ FORMATED DATA TEST ################")
                #print(json.dumps(formated_data, indent=4))
                
                #return dict_data
                return formated_data
            else:
                print(f"API Error: {response.status_code} - {response.text}")
                return None
                
        except httpx.RequestError as exc:
            print(f"Connection error: {exc.request.url!r}")
            return None

@app.get("/client/{cli_id}", status_code=status.HTTP_200_OK)
async def fetch_client_data(cli_id: str, base_url: str = VIGO_URL, token: str = TOKEN):
    if not base_url or not token:
        print("Error: Missing VIGO_BASE_URL or TOKEN in environment.")
        return None
    
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

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(cli_url, json=payload, headers=headers)

            if response.status_code==200:
                data =  response.json()

                if data.get("situacao") == "L":
                    return data
                
                return {"message": f"Client {cli_id} is not 'L'. Current status: {data.get('situacao')}"}
            else:
                print(f"API Error: {response.status_code} - {response.text}")
                return None
        except httpx.RequestError as exc:
            print(f"Connection error: {exc.request.url!r}")
            return None
        
@app.get("/marker_create/{os_id}")
async def marker_create(os_id: str):
    os_data = await fetch_os_details(os_id, VIGO_URL, TOKEN)
    client_data = await fetch_client_data(os_data['cli_id'], VIGO_URL, TOKEN)
    lon = client_data.get('longitude')
    lat = client_data.get('latitude')
    if not lon or not lat:
        print(f"Error: Missing coordinates for client {os_data.get('cli_id')}")
    clean_description = os_data['os_desc'].replace('\r\n', '<br>').replace('\n', '<br>')

    print("################ os_data ################")
    print(f"Longitude = {client_data['longitude']}, Latitude = {client_data['latitude']}")
    print(json.dumps(os_data, indent=4))

    kml = simplekml.Kml()
    kml.newpoint(
        name=f"{os_data['cli_id']} - {os_data['cli_name']}", 
        coords=[(lon, lat)], 
        description=(
            f"SUPORTE A SER REALIZADO<br><br>"
            f"{os_data['cli_id']} - {os_data['cli_name']}<br><br>"
            f"LOGIN: {os_data['cli_login']}<br>"
            f"SENHA: {os_data['cli_pass']}<br>"
            f"PAINEL: {os_data['cli_panel']}<br><br>"
            f"Localização: {os_data['cli_loc']}<br>"
            f"Endereço: {os_data['cli_address']}<br><br>"
            f"Solucionar:<br>{clean_description}"
        )
    )

    filename = f"OS_{os_id}_MAP.kml"
    kml.save(filename)
    
    if os.path.exists(filename):
        return FileResponse(path=filename, filename=filename, media_type='application/vnd.google-earth.kml+xml')
    return {"error": "File generation failed"}

@app.get("/get_open_os/")
async def fetch_os_by_filter(campo1: str = "h_fechamento", valor1: str = "", campo2: str = "dt_fechamento", valor2: str = "0001-01-01T00:00:00"):
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

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                list_opened_os = response.json()

                city_os = [
                    {
                    "cli_id":os["id_cliente"],
                    "cli_name":os["nome"],
                    "cli_login":None,
                    "cli_pass":None,
                    "cli_panel":None,
                    "Tipo":os["desc_tatendimento"],
                    "cli_loc":os["anotacao_tecnica"],
                    "cli_address":None,
                    "os_desc":os["historico"]
                } for os in list_opened_os if os['cidade'] == "Catalão" and os['desc_tatendimento'] == "Suporte (rádio/fibra)"
                ]
                
                return city_os
            else:
                print(f"Erro na API: {response.status_code} - {response.text}")
                return None
        except httpx.RequestError as exc:
            print(f"Erro de conexão ao buscar filtros: {exc}")
            return None
        
@app.get("/list_marker_create/")
async def create_marker_list():
    os_list = await fetch_os_by_filter()
    
    kml = simplekml.Kml()

    for os in os_list:
        client_data = await fetch_client_data(os['cli_id'], VIGO_URL, TOKEN)
        if not client_data:
            continue
        lon = client_data.get('longitude')
        lat = client_data.get('latitude')
        
        if not lon or not lat:
            print(f"Error: Missing coordinates for client {os.get('cli_id')}")
            continue

        clean_description = os['os_desc'].replace('\r\n', '<br>').replace('\n', '<br>')

        kml.newpoint(
            name=f"{os['cli_id']} - {os['cli_name']}", 
            coords=[(lon, lat)], 
            description=(
                f"SUPORTE A SER REALIZADO<br><br>"
                f"{os['cli_id']} - {os['cli_name']}<br><br>"
                f"LOGIN: {os['cli_login']}<br>"
                f"SENHA: {os['cli_pass']}<br>"
                f"PAINEL: {os['cli_panel']}<br><br>"
                f"Localização: {os['cli_loc']}<br>"
                f"Endereço: {os['cli_address']}<br><br>"
                f"Solucionar:<br>{clean_description}"
            )
        )

    filename = "OS_MAP_GLOBAL.kml"
    kml.save(filename)

    return {
        "status": f"Arquivo salvo localmente"
    }

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)