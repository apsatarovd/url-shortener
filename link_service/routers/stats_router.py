from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from link_service.database import get_db
from link_service.models import Link, ClickEvent
router = APIRouter()

@router.get("/stats/{short_code}")
async def get_stats(short_code: str, db: AsyncSession = Depends(get_db)):
    # 1. Ищем саму ссылку (асинхронный запрос)
    link_stmt = select(Link).where(Link.short_code == short_code)
    link_result = await db.execute(link_stmt)
    link = link_result.scalar_one_or_none()
    
    if not link:
        raise HTTPException(status_code=404, detail="Ссылка не найдена")
    
    link_id = link.id

    count_stmt = select(func.count(ClickEvent.id)).where(ClickEvent.link_id == link_id)
    count_result = await db.execute(count_stmt)
    total_clicks = count_result.scalar() or 0

    device_stmt = select(ClickEvent.user_agent, func.count(ClickEvent.id)).where(
        ClickEvent.link_id == link_id
    ).group_by(ClickEvent.user_agent)
    device_result = await db.execute(device_stmt)
    devices_raw = device_result.all()
    devices = {device: count for device, count in devices_raw}

    source_stmt = select(ClickEvent.referer, func.count(ClickEvent.id)).where(
        ClickEvent.link_id == link_id
    ).group_by(ClickEvent.referer)
    source_result = await db.execute(source_stmt)
    sources_raw = source_result.all()
    sources = {source: count for source, count in sources_raw}

    date_stmt = select(
        func.date(ClickEvent.clicked_at), 
        func.count(ClickEvent.id)
    ).where(
        ClickEvent.link_id == link_id
    ).group_by(func.date(ClickEvent.clicked_at))
    
    date_result = await db.execute(date_stmt)
    dates_raw = date_result.all()
    
    by_day = {str(date): count for date, count in dates_raw}
    
    return {
        "short_code": short_code,
        "total_clicks": total_clicks,
        "by_day": by_day, 
        "by_device": devices,
        "by_source": sources
        
    }

