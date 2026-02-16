import asyncio
from app.vigo_client import get_auth_token

async def test_connection():
    print("Tentando conectar ao VIGO...")
    token = await get_auth_token()
    
    if token:
        print("✅ SUCESSO! Token recebido:")
        print(f"Token: {token}")
    else:
        print("❌ FALHA: Não foi possível obter o token. Verifique a URL e as credenciais no .env.")

if __name__ == "__main__":
    asyncio.run(test_connection())