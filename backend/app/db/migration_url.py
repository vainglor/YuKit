def sync_database_url(url: str) -> str:
    return url.replace("+asyncpg", "+psycopg").replace("+aiosqlite", "")
