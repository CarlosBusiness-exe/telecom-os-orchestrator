import httpx
import asyncio
import os
import json
from typing import List, Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv

from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import simplekml

load_dotenv()

# --- Configurações ---
VIGO_URL = os.getenv("VIGO_BASE_URL")
VIGO_LOGIN = os.getenv("VIGO_LOGIN")
VIGO_PASS = os.getenv("VIGO_SENHA")
CURRENT_TOKEN = os.getenv("TOKEN")

class DashboardOrder(BaseModel):
    os_id: int
    cli_id: int
    cli_name: str
    bairro: str
    cidade: str
    abertura: str
    hora: str
    tipo: str
    funcionario: str
    descricao: str
    agendamento: Optional[str]
    valor: float

app = FastAPI(title="Cbnet Support System Unified")

# Monta arquivos estáticos
app.mount("/static", StaticFiles(directory="src/v1/static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared HTTP Client
http_client = httpx.AsyncClient(
    limits=httpx.Limits(max_keepalive_connections=50, max_connections=100),
    timeout=15.0
)

# --- Camada de Comunicação VIGO (Padronizada) ---
async def refresh_token():
    global CURRENT_TOKEN
    url = f"{VIGO_URL}/api/auth"
    payload = {"login": str(VIGO_LOGIN), "senha": str(VIGO_PASS)}
    try:
        response = await http_client.post(url, json=payload)
        if response.status_code == 200:
            CURRENT_TOKEN = response.json().get("senha")
            return CURRENT_TOKEN
    except Exception: return None

async def vigo_request(method: str, endpoint: str, payload: dict = None):
    global CURRENT_TOKEN
    url = f"{VIGO_URL}{endpoint}"
    def get_headers():
        return {"Authorization": f"Bearer {CURRENT_TOKEN}", "Content-Type": "application/json"}
    
    response = await http_client.request(method, url, json=payload, headers=get_headers())
    if response.status_code == 401:
        if await refresh_token():
            response = await http_client.request(method, url, json=payload, headers=get_headers())
    return response

async def fetch_client_data(cli_id: str):
    payload = {"campo1": "ID", "campo1_valor": str(cli_id), "campo2": "none", "campo2_valor": "none"}
    response = await vigo_request("POST", "/api/app_getcliente", payload)
    if response.status_code == 200:
        return response.json()
    raise HTTPException(status_code=response.status_code, detail="Client API Error")

async def fetch_order_by_filter(cidade: str, tipo: str):
    """Lógica de filtro original da sua V1 - ATUALIZADA"""
    payload = {"campo1": "h_fechamento", "campo1_valor": "", "campo2": None, "campo2_valor": None}
    response = await vigo_request("POST", "/api/app_getcustom", payload)
    
    if response.status_code == 200:
        orders = response.json()
        return [
            {
                "cli_id": o["id_cliente"],
                "cli_name": o["nome"],
                "Tipo": o["desc_tatendimento"],
                "cli_loc": o["anotacao_tecnica"],
                "order_desc": o["historico"],
                "cidade": o.get("cidade"),
                "desc_tatendimento": o.get("desc_tatendimento"),
                "anotacao_tecnica": o.get("anotacao_tecnica"),
                "endereco": o.get("endereco"),
                "bairro": o.get("bairro")
            } for o in orders if o.get('cidade') == cidade and o.get('desc_tatendimento') == tipo
        ]
    return []

# --- ENDPOINTS V1 (Maps Integrado) ---
@app.get("/maps", response_class=HTMLResponse)
async def serve_v1_maps():
    with open("src/v2/static/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/list_marker_create/")
async def create_marker_list(cidade: str = "catalao", tipo: str = "suporte"):
    CITY_MAP = {"catalao": "Catalão", "ouvidor": "Ouvidor", "davinopolis": "Davinópolis"}
    TYPE_MAP = {"suporte": "Suporte (rádio/fibra)", "rural": "Suporte Rural", "retirada": "Retirada"}

    cidade_real = CITY_MAP.get(cidade, "Catalão")
    tipo_real = TYPE_MAP.get(tipo, "Suporte (rádio/fibra)")

    order_list = await fetch_order_by_filter(cidade=cidade_real, tipo=tipo_real)
    if not order_list:
        raise HTTPException(status_code=404, detail="Nenhuma OS encontrada para o filtro informado.")

    return await _create_kml_file(order_list, "order_MAP_GLOBAL.kml")

async def _create_kml_file(order_list, filename):
    if not order_list:
        raise HTTPException(status_code=404, detail="Nenhuma OS encontrada para gerar KML.")

    kml = simplekml.Kml()

    for order in order_list:
        try:
            client = await fetch_client_data(order['cli_id'])
            lon = client.get('longitude', "-47.946797")
            lat = client.get('latitude', "-18.158900")

            if not lon or not lat or str(lon) == "0":
                lon, lat = "-47.946797", "-18.158900"

            clean_desc = order['order_desc'].replace('\r\n', '<br>').replace('\n', '<br>')

            balloon_content = (
                f"SUPORTE A SER REALIZADO<br><br>"
                f"{order['cli_id']} - {order['cli_name']}<br><br>"
                f"LOGIN: None<br>"
                f"SENHA: None<br>"
                f"PAINEL: None<br><br>"
                f"Localização: {order.get('anotacao_tecnica', 'N/A')}<br>"
                f"Endereço: {order.get('endereco', 'N/A')}, {order.get('bairro', 'N/A')}, {order.get('cidade', 'N/A')}<br><br>"
                f"Solucionar:<br>"
                f"{clean_desc}<br>"
                f"===========================================<br>"
            )

            kml.newpoint(
                name=f"{order['cli_id']} - {order['cli_name']}",
                coords=[(lon, lat)],
                description=balloon_content
            )
        except Exception as e:
            print(f"Erro ao criar ponto para OS {order.get('cli_id')}: {e}")
            continue

    kml.save(filename)
    return FileResponse(path=filename, filename=filename, media_type='application/vnd.google-earth.kml+xml')

@app.get("/marker_create/{os_id}")
async def create_single_os_map(os_id: int):
    payload = {"campo1": "h_fechamento", "campo1_valor": "", "campo2": None, "campo2_valor": None}
    response = await vigo_request("POST", "/api/app_getcustom", payload)

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Erro ao consultar OS para fins de mapa.")

    orders = response.json()
    order = next((o for o in orders if o.get("id") == os_id), None)

    if not order:
        raise HTTPException(status_code=404, detail=f"OS {os_id} não encontrada.")

    order_data = {
        "cli_id": order.get("id_cliente"),
        "cli_name": order.get("nome"),
        "Tipo": order.get("desc_tatendimento"),
        "cli_loc": order.get("anotacao_tecnica"),
        "order_desc": order.get("historico", ""),
        "cidade": order.get("cidade"),
        "desc_tatendimento": order.get("desc_tatendimento"),
        "anotacao_tecnica": order.get("anotacao_tecnica"),
        "endereco": order.get("endereco"),
        "bairro": order.get("bairro"),
        "cidade": order.get("cidade")
    }

    return await _create_kml_file([order_data], f"order_{os_id}.kml")

# --- LÓGICA V2: Dashboard Backend ---
async def get_filtered_support_orders(tipo_filtro: Optional[str] = None, data_filtro: Optional[str] = None):
    payload = {"campo1": "h_fechamento", "campo1_valor": ""}
    response = await vigo_request("POST", "/api/app_getcustom", payload)
    if response.status_code != 200: return []
    
    raw_data = response.json()
    ALLOWED_TYPES = ["Suporte (rádio/fibra)", "Suporte Rural", "Help Desk", "Retirada (fibra/rádio)"]
    ALLOWED_CITY = ["Catalão"]
    
    types_to_filter = [tipo_filtro] if tipo_filtro in ALLOWED_TYPES else ALLOWED_TYPES
    
    structured_orders = []
    for item in raw_data:
        if item.get("desc_tatendimento") not in types_to_filter: continue
        if item.get("cidade") not in ALLOWED_CITY: continue
        if data_filtro and (not item.get("dt_agendamento") or data_filtro not in item.get("dt_agendamento")): continue
        
        structured_orders.append(DashboardOrder(
            os_id=item.get("id"), cli_id=item.get("id_cliente"), cli_name=item.get("nome"),
            bairro=item.get("bairro", "N/A"), cidade=item.get("cidade"), abertura=item.get("dt_abertura", ""),
            hora=item.get("h_abertura", ""), tipo=item.get("desc_tatendimento", ""),
            funcionario=item.get("desc_funcionario", ""), descricao=item.get("descricao", ""),
            agendamento=item.get("dt_agendamento"), valor=float(item.get("valor", 0))
        ))
    return structured_orders

@app.get("/api/dashboard/orders", response_model=List[DashboardOrder])
async def dashboard_orders(tipo: Optional[str] = Query(None), data: Optional[str] = Query(None)):
    orders = await get_filtered_support_orders(tipo_filtro=tipo, data_filtro=data)
    if not orders: raise HTTPException(status_code=404, detail="Nenhuma OS encontrada.")
    return orders

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    with open("src/v2/index.html", "r", encoding="utf-8") as f:
        return f.read()

# --- Cleanup ---
async def finish_order(order_id: int, employee_id: int = 146, note: str = "LIMPEZA OS ANTIGA"):
    payload = {"id_atendimento": int(order_id), "id_funcionario": int(employee_id), "texto": note}
    response = await vigo_request("POST", "/api/app_finish", payload)
    return response.status_code == 200

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)