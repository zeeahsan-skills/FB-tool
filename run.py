import sys
import asyncio
import uvicorn
from app.config import get_settings

# On Windows, SelectorEventLoop (used by default in some runners/threads) doesn't support subprocesses.
# ProactorEventLoop is required for asyncio subprocesses used by Playwright.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

if __name__ == "__main__":
    settings = get_settings()
    print(f"Starting Facebook Group Research Agent at http://{settings.APP_HOST}:{settings.APP_PORT}")
    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        loop="asyncio",
        reload=False,
    )
