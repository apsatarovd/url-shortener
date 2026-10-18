import os
from fastapi import Header, HTTPException

async def verify_api_key(x_api_key: str = Header(...)):
    correct_key = os.getenv("API_KEY")
    
    if not correct_key or x_api_key != correct_key:
        raise HTTPException(status_code=401, detail="Неверный API-ключ")
    
    return x_api_key
