from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi_pagination import add_pagination

from api import main_router
from config import get_config
from database import set_tables
from utils.logger import logger

cfg = get_config()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Start app!")
    # await drop_tables()
    await set_tables()
    yield
    logger.info("End app!")


app = FastAPI(lifespan=lifespan)
add_pagination(app)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> Response:
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"status": "error", "message": f"Ошибка в данных запроса. {exc}"},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> Response:
    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"status": "error", "message": "Пользователь не авторизован."},
        )
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.detail,  # стандартный формат FastAPI
        headers=exc.headers,
    )


app.include_router(main_router)


@app.get("/api/ping")
async def ping():
    return {"result": "PROOOOOOOOOOOOD"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True, log_level="debug")
