import httpx
import asyncio
import os
from typing import List, Optional
from dotenv import load_dotenv

from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

load_dotenv()

# --- Configuration ---
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

app = FastAPI(title="Cbnet Support Dashboard")

# Permite requisições do frontend
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

# --- VIGO Communication Layer ---
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


# --- Core Logic com Filtro de Data ---
async def get_filtered_support_orders(cidade_filtro: Optional[str] = None, tipo_filtro: Optional[str] = None, data_filtro: Optional[str] = None):
    payload = {"campo1": "h_fechamento", "campo1_valor": ""}
    response = await vigo_request("POST", "/api/app_getcustom", payload)
    
    if response.status_code != 200:
        return []

    raw_data = response.json()
    ALLOWED_TYPES = ["Suporte (rádio/fibra)", "Suporte Rural"]
    ALLOWED_CITY = ["Catalão"]

    # Se um tipo for selecionado, filtramos apenas ele, caso contrário, pegamos ambos
    types_to_filter = [tipo_filtro] if tipo_filtro in ALLOWED_TYPES else ALLOWED_TYPES

    structured_orders = []
    for item in raw_data:
        # Filtros de Tipo e Cidade
        if item.get("desc_tatendimento") not in types_to_filter: continue
        if item.get("cidade") not in ALLOWED_CITY: continue
        
        # Filtro de Data de Agendamento (Comparação de String YYYY-MM-DD)
        if data_filtro:
            # O VIGO retorna dt_agendamento como '2026-03-23T00:00:00'
            # O input date do HTML envia '2026-03-23'
            dt_vigo = item.get("dt_agendamento", "")
            if not dt_vigo or data_filtro not in dt_vigo:
                continue

        structured_orders.append(DashboardOrder(
            os_id=item.get("id"),
            cli_id=item.get("id_cliente"),
            cli_name=item.get("nome"),
            bairro=item.get("bairro", "N/A"),
            cidade=item.get("cidade"),
            abertura=item.get("dt_abertura", ""),
            hora=item.get("h_abertura", ""),
            tipo=item.get("desc_tatendimento", ""),
            funcionario=item.get("desc_funcionario", ""),
            descricao=item.get("descricao", ""),
            agendamento=item.get("dt_agendamento"),
            valor=float(item.get("valor", 0))
        ))

    return structured_orders

@app.get("/api/dashboard/orders", response_model=List[DashboardOrder])
async def dashboard_orders(
    cidade: Optional[str] = Query(None), 
    tipo: Optional[str] = Query(None),
    data: Optional[str] = Query(None) # Novo parâmetro
):
    orders = await get_filtered_support_orders(cidade_filtro=cidade, tipo_filtro=tipo, data_filtro=data)
    if not orders:
        raise HTTPException(status_code=404, detail="Nenhuma OS encontrada.")
    return orders

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    with open("src/v2/index.html", "r", encoding="utf-8") as f:
        return f.read()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)