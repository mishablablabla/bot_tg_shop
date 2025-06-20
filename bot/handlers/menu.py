from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from services.store_service import list_regions, list_stores
from db.session import SessionLocal
from db.models import User, Location
from bot.handlers.common import FSM, control_buttons

router = Router()

@router.callback_query(FSM.MAIN_MENU, lambda c: c.data == "menu_locations")
async def main_menu_handler(callback: types.CallbackQuery, state: FSMContext):
    """
    Обработка кнопки "Lokacje/Dzielnice" из главного меню.
    """
    await state.update_data(menu_source="main_menu")

    db = SessionLocal()
    try:
        user = db.query(User).filter_by(telegram_id=callback.from_user.id).first()
        if user and user.city:
            loc = db.query(Location).filter_by(city=user.city).first()
            await state.update_data(region=loc.region, city=user.city)

            stores = list_stores(loc.region, user.city)
            if stores:
                rows = [
                    [types.InlineKeyboardButton(text=s, callback_data=f"store:{s}")]
                    for s in stores
                ]
                rows += control_buttons()
                kb = types.InlineKeyboardMarkup(inline_keyboard=rows)

                try:
                    await callback.message.edit_text(
                        f"Zapisany region: {loc.region}\n"
                        f"Zapisane miasto: {user.city}\n"
                        "Wybierz sklep:",
                        reply_markup=kb
                    )
                except TelegramBadRequest as e:
                    if "message is not modified" in str(e):
                        await callback.answer()
                    else:
                        raise
                await state.set_state(FSM.STORE)
                return
            else:
                await callback.answer("Brak sklepów w tym mieście.", show_alert=True)
    finally:
        db.close()

    # Если город не задан или нет магазинов — показываем регионы
    regions = list_regions()
    rows = [
        [types.InlineKeyboardButton(text=r, callback_data=f"region:{r}")]
        for r in regions
    ]
    rows += control_buttons(back=False)
    kb = types.InlineKeyboardMarkup(inline_keyboard=rows)

    try:
        await callback.message.edit_text(
            "Wybierz region:", 
            reply_markup=kb
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            await callback.answer()
        else:
            raise

    await state.set_state(FSM.REGION)
