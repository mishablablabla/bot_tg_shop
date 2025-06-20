from .common import router as common_router
from .location import router as location_router
from .order import router as order_router
from .menu import router as menu_router
from .info import router as info_router

routers = [
    common_router,
    location_router,
    order_router,
    menu_router,
    info_router,
]