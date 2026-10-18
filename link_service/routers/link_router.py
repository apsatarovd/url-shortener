import random
import string

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from link_service.auth import verify_api_key
from link_service.database import get_db
from link_service.models import ClickEvent, Link
from link_service.rabbit_client import publish_click_event
from link_service.redis_client import redis_client
from link_service.schemas import LinkCreate, LinkResponse

router = APIRouter(prefix="/api", tags=["Links"])

def generate_short_code(length=6):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

@router.post("/shorten", response_model=LinkResponse)
async def create_short_link(data: LinkCreate, db: AsyncSession = Depends(get_db),
     api_key: str = Depends(verify_api_key) ):
  
    while True:
        short_code = generate_short_code()
        
        result = await db.execute(select(Link).where(Link.short_code == short_code))
        existing_link = result.scalar_one_or_none()
        
        if not existing_link:
            break 

    new_link = Link(original_url=str(data.original_url), short_code=short_code)
    
    db.add(new_link)
    await db.commit()
    await db.refresh(new_link)
    
    return new_link

@router.get("/links")
async def get_all_links_with_stats(db: AsyncSession = Depends(get_db),api_key: str = Depends(verify_api_key)):
    stmt = (
        select(
            Link.short_code,
            Link.original_url,
            Link.created_at,
            func.count(ClickEvent.id).label("total_clicks")
        )
        .outerjoin(ClickEvent, Link.id == ClickEvent.link_id)
        .group_by(Link.id)
        .order_by(Link.created_at.desc()) 
    )
    
    result = await db.execute(stmt)
    rows = result.all()
    
    return [
        {
            "short_code": row.short_code,
            "original_url": row.original_url,
            "total_clicks": row.total_clicks,
            "created_at": row.created_at.isoformat() if row.created_at else None
        }
        for row in rows
    ]

@router.get("/{short_code}")
async def redirect_to_original(short_code: str, request: Request, db: AsyncSession = Depends(get_db),):

    original_url = None 
    link_id = None

    try:
        original_url = await redis_client.get(f"link:{short_code}")
    except Exception as e:
        print(f" Redis недоступен: {e}. Переключаемся на PostgreSQL.")
    
    if not original_url:
        print(f" [POSTGRES] Запрос в базу для кода: {short_code}")
        
        result = await db.execute(select(Link).where(Link.short_code == short_code))
        link = result.scalar_one_or_none()
        
        if not link:
            raise HTTPException(status_code=404, detail="Short link not found")
        
        original_url = link.original_url
        link_id = link.id

        try:
            await redis_client.setex(f"link:{short_code}", 3600, original_url)
        except Exception:
            pass
    else:
        print(f"[REDIS] Быстрый ответ из кэша для кода: {short_code}")

        result = await db.execute(select(Link.id).where(Link.short_code == short_code))
        link_id = result.scalar_one()

    ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "")
    referer = request.headers.get("referer", "")
    
    # Отправляем в RabbitMQ в фоне
    await publish_click_event(link_id, short_code, ip, user_agent, referer)
            
    
    return RedirectResponse(url=original_url, status_code=302)


