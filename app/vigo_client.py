import httpx
import os
from dotenv import load_dotenv

# Tenta carregar o arquivo .env da pasta atual
load_dotenv()

VIGO_URL = os.getenv("VIGO_BASE_URL")
LOGIN = os.getenv("VIGO_LOGIN")
SENHA = os.getenv("VIGO_SENHA")

async def get_auth_token():
    url = f"{VIGO_URL}/api/auth"
     
    payload = {
        "login": str(LOGIN).strip(),
        "senha": str(SENHA).strip()
    }
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                dados = response.json()
                return dados.get("senha") 
            else:
                print(f"Erro na autenticação: {response.status_code} - {response.text}")
                return None
                
    except Exception as e:
        print(f"Erro ao conectar com a API: {e}")
        return None
    
