import re
import json as j
from fastapi import APIRouter, HTTPException
from src.core.config import settings
import httpx

router = APIRouter(prefix="/stats", tags=["Stats / Analytics"])

CLICKHOUSE_HTTP = f"http://{settings.CLICKHOUSE_HOST}:{settings.CLICKHOUSE_HTTP_PORT}"
CLICKHOUSE_USER = settings.CLICKHOUSE_USER
CLICKHOUSE_PASS = settings.CLICKHOUSE_PASSWORD


# Только безопасные символы для имён (SQL injection protection)
_SAFE_NAME = re.compile(r"^[a-zA-Z0-9_\-]+$")


async def _ch_query(query: str) -> list:
    """Выполнить запрос к ClickHouse через HTTP, Basic Auth, вернуть список dict"""
    query = query.rstrip().rstrip(";") + "\nFORMAT JSONEachRow"
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            CLICKHOUSE_HTTP,
            data=query,
            auth=(CLICKHOUSE_USER, CLICKHOUSE_PASS),
            timeout=10,
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail=f"ClickHouse error: {resp.text}")
        if not resp.text.strip():
            return []
        return [j.loads(line) for line in resp.text.strip().split("\n") if line.strip()]


@router.get("/{experiment_name}")
async def get_experiment_stats(experiment_name: str):
    """Агрегированная статистика по эксперименту"""
    if not _SAFE_NAME.match(experiment_name):
        raise HTTPException(status_code=400, detail="Недопустимое имя эксперимента")
    try:
        # 1. Общая сводка
        summary = await _ch_query(f"""
            SELECT
                variant,
                count() AS total_events,
                countDistinct(user_id) AS unique_users,
                min(timestamp) AS first_event,
                max(timestamp) AS last_event
            FROM tracking_events
            WHERE experiment_name = '{experiment_name}'
            GROUP BY variant
            ORDER BY variant
        """)

        # 2. События по типам
        by_event = await _ch_query(f"""
            SELECT
                variant,
                event_name,
                count() AS cnt,
                countDistinct(user_id) AS users
            FROM tracking_events
            WHERE experiment_name = '{experiment_name}'
            GROUP BY variant, event_name
            ORDER BY variant, event_name
        """)

        # 3. CTA конверсия: пользователи, кто сделал page_view → cta_click
        funnel = await _ch_query(f"""
            SELECT
                pv.variant,
                pv.views,
                COALESCE(cc.clicks, 0) AS clicks,
                round(COALESCE(cc.clicks, 0) / pv.views * 100, 1) AS conversion_pct
            FROM (
                SELECT variant, countDistinct(user_id) AS views
                FROM tracking_events
                WHERE experiment_name = '{experiment_name}' AND event_name = 'page_view'
                GROUP BY variant
            ) pv
            LEFT JOIN (
                SELECT variant, countDistinct(user_id) AS clicks
                FROM tracking_events
                WHERE experiment_name = '{experiment_name}' AND event_name = 'cta_click'
                GROUP BY variant
            ) cc ON pv.variant = cc.variant
            ORDER BY pv.variant
        """)

        # 4. Последние события
        recent = await _ch_query(f"""
            SELECT timestamp, user_id, event_name, variant, event_data
            FROM tracking_events
            WHERE experiment_name = '{experiment_name}'
            ORDER BY timestamp DESC
            LIMIT 20
        """)

        return {
            "experiment": experiment_name,
            "summary": summary,
            "by_event": by_event,
            "funnel": funnel,
            "recent": recent,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stats error: {str(e)}")
