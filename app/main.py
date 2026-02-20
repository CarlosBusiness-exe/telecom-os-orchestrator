import httpx
import asyncio
import os
import json
from dotenv import load_dotenv

from fastapi import FastAPI
from fastapi import status

import simplekml

app: FastAPI = FastAPI(title="OS Orchstrator")

load_dotenv()

VIGO_URL = os.getenv("VIGO_BASE_URL")
TOKEN = os.getenv("TOKEN")

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
                return response.json()
            else:
                print(f"API Error: {response.status_code} - {response.text}")
                return None
        except httpx.RequestError as exc:
            print(f"Connection error: {exc.request.url!r}")
            return None
        
@app.get("/marker_create/{os_id}", status_code=status.HTTP_200_OK)
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
    kml.save(f"OS_{os_id}_MAP.kml")

    return os_data

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)