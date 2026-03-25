import httpx
import asyncio
import os
import json
from dotenv import load_dotenv

from fastapi import FastAPI, status, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse

import simplekml
from datetime import datetime, timedelta

load_dotenv()

VIGO_URL = os.getenv("VIGO_BASE_URL")
VIGO_LOGIN = os.getenv("VIGO_LOGIN")
VIGO_PASS = os.getenv("VIGO_SENHA")

CURRENT_TOKEN = os.getenv("TOKEN")

app = FastAPI(title="Service Order Orchestrator")
app.mount("/static", StaticFiles(directory="src/v1/static"), name="static")

# Shared HTTP Client for efficiency
http_client = httpx.AsyncClient(
    limits=httpx.Limits(max_keepalive_connections=50, max_connections=100),
    timeout=10.0
)

async def refresh_token():
    """Authenticates with VIGO API to get a new token."""
    global CURRENT_TOKEN
    url = f"{VIGO_URL}/api/auth"
    payload = {"login": str(VIGO_LOGIN), "senha": str(VIGO_PASS)}
    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    try:
        response = await http_client.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            data = response.json()
            CURRENT_TOKEN = data.get("senha")
            print(">>> Token refreshed successfully.")
            return CURRENT_TOKEN
        else:
            print(f">>> Auth Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f">>> Connection Error during Auth: {e}")
        return None

async def vigo_request(method: str, endpoint: str, payload: str = None):
    """
    Wrapper for all VIGO API calls. 
    Handles 'Bearer' headers and automatic 401 re-authentication.
    """
    global CURRENT_TOKEN
    url = f"{VIGO_URL}{endpoint}"
    
    def get_headers():
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {CURRENT_TOKEN}"
        }

    # Attempt 1
    response = await http_client.request(method, url, json=payload, headers=get_headers())

    # If Unauthorized (401), try to refresh token once
    if response.status_code == 401:
        print(">>> Token expired (401). Attempting automatic refresh...")
        if await refresh_token():
            # Attempt 2 with new token
            response = await http_client.request(method, url, json=payload, headers=get_headers())
    
    return response

@app.get("/", response_class=HTMLResponse)
async def index():
    with open("src/v1/static/index.html", "r") as f:
        return f.read()

@app.get("/order/{order_id}")
async def fetch_order_details(order_id: str):
    payload = {"campo1": "id", "campo1_valor": str(order_id), "campo2": "none", "campo2_valor": "none"}
    
    response = await vigo_request("POST", "/api/app_getcustom", payload)
    
    if response.status_code == 200:
        list_data = response.json()
        if not list_data:
            raise HTTPException(status_code=404, detail="Order not found")
        
        dict_data = list_data[0]
        return dict_data
        """return {
            "cli_id": dict_data["id_cliente"],
            "cli_name": dict_data["nome"],
            "cli_login": "",
            "cli_pass": "",
            "cli_panel": "",
            "cli_loc": dict_data["anotacao_tecnica"],
            "cli_address": "",
            "order_desc": dict_data["historico"]
        }"""
    raise HTTPException(status_code=response.status_code, detail="VIGO API Error")

@app.get("/client/{cli_id}")
async def fetch_client_data(cli_id: str):
    payload = {"campo1": "ID", "campo1_valor": str(cli_id), "campo2": "none", "campo2_valor": "none"}
    
    response = await vigo_request("POST", "/api/app_getcliente", payload)

    if response.status_code == 200:
        data = response.json()
        return data
        if data.get("situacao") == "L":
            return data
        raise HTTPException(status_code=403, detail=f"Client status is {data.get('situacao')}")
    raise HTTPException(status_code=response.status_code, detail="Client API Error")

@app.get("/get_open_order/")
async def fetch_order_by_filter(cidade: str = "Catalão", tipo: str = "Suporte (rádio/fibra)"):
    payload = {"campo1": "h_fechamento", "campo1_valor": "", "campo2": None, "campo2_valor": None}
    
    response = await vigo_request("POST", "/api/app_getcustom", payload)
    
    if response.status_code == 200:
        orders = response.json()
        # Filter logic
        return [
            {
                "cli_id": o["id_cliente"],
                "cli_name": o["nome"],
                "cli_login": "",
                "cli_pass": "",
                "cli_panel": "",
                "Tipo": o["desc_tatendimento"],
                "cli_loc": o["anotacao_tecnica"],
                "cli_address": "",
                "order_desc": o["historico"]
            } for o in orders if o.get('cidade') == cidade and o.get('desc_tatendimento') == tipo
        ]
    raise HTTPException(status_code=response.status_code, detail="Filter API Error")

@app.get("/list_marker_create/")
async def create_marker_list(cidade: str = "catalao", tipo: str = "suporte"):
    CITY_MAP = {"catalao": "Catalão", "ouvidor": "Ouvidor", "davinopolis": "Davinópolis"}
    TYPE_MAP = {"suporte": "Suporte (rádio/fibra)", "rural": "Suporte Rural", "retirada": "Retirada"}
    
    cidade_real = CITY_MAP.get(cidade, "Catalão")
    tipo_real = TYPE_MAP.get(tipo, "Suporte (rádio/fibra)")

    order_list = await fetch_order_by_filter(cidade=cidade_real, tipo=tipo_real)
    kml = simplekml.Kml()

    for order in order_list:
        try:
            client = await fetch_client_data(order['cli_id'])
            lon = client.get('longitude', "-47.946797")
            lat = client.get('latitude', "-18.158900")
            
            if not lon or not lat or str(lon) == "0":
                lon, lat = "-47.946797", "-18.158900"

            clean_desc = order['order_desc'].replace('\r\n', '<br>').replace('\n', '<br>')

            kml.newpoint(
                name=f"{order['cli_id']} - {order['cli_name']}",
                coords=[(lon, lat)],
                description=f"<b>OS:</b> {clean_desc}<br><b>Loc:</b> {order['cli_loc']}"
            )
        except Exception:
            continue

    filename = "order_MAP_GLOBAL.kml"
    kml.save(filename)
    return FileResponse(path=filename, filename=filename, media_type='application/vnd.google-earth.kml+xml')

async def finish_order(order_id: int, employee_id: int = 146, note: str = "LIMPEZA OS ANTIGA"):
    """
    Tenta encerrar a OS. 
    Mude o employee_id para o SEU ID no VIGO se o 146 não funcionar.
    """
    payload = {
        "id_atendimento": int(order_id),
        "id_funcionario": int(employee_id),
        "texto": note
    }
    
    response = await vigo_request("POST", "/api/app_finish", payload)
    
    if response.status_code != 200:
        # ISSO VAI NOS DIZER O MOTIVO REAL DA FALHA
        print(f">>> ERRO AO FECHAR OS {order_id}: {response.status_code} - {response.text}")
        return False
    
    print(f">>> OS {order_id} FECHADA COM SUCESSO.")
    return True

@app.post("/cleanup_phantom_orders/")
async def cleanup_phantom_orders(dry_run: bool = True):
    # 1. Busca todas as OS onde h_fechamento está vazio
    payload = {"campo1": "h_fechamento", "campo1_valor": "", "campo2": None, "campo2_valor": None}
    response = await vigo_request("POST", "/api/app_getcustom", payload)
    
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Erro ao buscar dados no VIGO.")

    all_orders = response.json()
    now = datetime.now()
    one_year_ago = now - timedelta(days=365)
    
    to_close = []

    for order in all_orders:
        dt_abertura = order.get("dt_abertura")
        if dt_abertura:
            try:
                open_date = datetime.fromisoformat(dt_abertura)
                if open_date < one_year_ago:
                    to_close.append({
                        "id": order.get("id"),
                        "nome": order.get("nome"),
                        "data": dt_abertura
                    })
            except Exception:
                continue

    if dry_run:
        return {"modo": "DRY_RUN", "total": len(to_close), "lista": to_close}

    # 2. Execução: Tenta fechar uma por uma
    closed = 0
    for item in to_close:
        success = await finish_order(item["id"])
        if success:
            closed += 1
            # Pequeno delay para não sobrecarregar a API local
            await asyncio.sleep(0.1) 

    return {"modo": "EXECUCAO", "total_tentativas": len(to_close), "sucessos": closed}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)