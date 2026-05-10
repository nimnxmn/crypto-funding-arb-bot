import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import meta, scanner, positions, funding, risk, balances, pnl, mode, config_route, reset as reset_route
from api.ws import manager, websocket_endpoint, broadcast_loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(broadcast_loop())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="ARB_bot API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(meta.router, prefix="/api")
app.include_router(scanner.router, prefix="/api")
app.include_router(positions.router, prefix="/api/positions")
app.include_router(funding.router, prefix="/api/funding")
app.include_router(risk.router, prefix="/api/risk")
app.include_router(balances.router, prefix="/api/balances")
app.include_router(pnl.router, prefix="/api/pnl")
app.include_router(mode.router, prefix="/api")
app.include_router(config_route.router, prefix="/api")
app.include_router(reset_route.router, prefix="/api")

from fastapi import WebSocket
app.add_api_websocket_route("/ws", websocket_endpoint)
