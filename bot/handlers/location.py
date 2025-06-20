from aiogram import Router, types
from aiogram.fsm.context import FSMContext

from services.store_service import list_regions, list_cities, list_stores
from db.session import SessionLocal
from db.models import User
from bot.handlers.common import FSM, control_buttons, show_main_menu
from aiogram.exceptions import TelegramBadRequest

router = Router()

@router.callback_query(FSM.MAIN_MENU, lambda c: c.data == "menu_change_city")
async def menu_change_city(callback: types.CallbackQuery, state: FSMContext):
    """
    Хэндлер для кнопки "Изменить город" в главном меню.
    """
    await state.update_data(menu_source="change_city")
    regions = list_regions()
    rows = [[types.InlineKeyboardButton(text=r, callback_data=f"region:{r}")] for r in regions]
    rows += control_buttons()
    kb = types.InlineKeyboardMarkup(inline_keyboard=rows)
    await callback.message.edit_text(
        "Wybierz region dla nowego miasta:",
        reply_markup=kb
    )
    await state.set_state(FSM.REGION)

@router.callback_query(FSM.REGION, lambda c: c.data.startswith("region:"))
async def choose_region(callback: types.CallbackQuery, state: FSMContext):
    """
    После выбора региона — показываем список городов.
    """
    region = callback.data.split(":", 1)[1]
    await state.update_data(region=region)

    cities = list_cities(region)
    if not cities:
        await callback.answer("Brak miast w tym regionie.", show_alert=True)
        return

    rows = [[types.InlineKeyboardButton(text=c, callback_data=f"city:{c}")] for c in cities]
    rows += control_buttons()
    kb = types.InlineKeyboardMarkup(inline_keyboard=rows)

    await callback.message.edit_text(
        f"Region: {region}\nWybierz miasto:",
        reply_markup=kb
    )
    await state.set_state(FSM.CITY)
    await callback.answer()

@router.callback_query(FSM.CITY, lambda c: c.data.startswith("city:"))
async def choose_city(callback: types.CallbackQuery, state: FSMContext):
    """
    После выбора города — сохраняем его в БД и либо возвращаем в меню, либо переходим к выбору магазина.
    """
    city = callback.data.split(":", 1)[1]
    data = await state.get_data()
    await state.update_data(city=city)

    # Сохраняем город в профиле, если пользователь уже был зарегистрирован
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(telegram_id=callback.from_user.id).first()
        if user:
            user.city = city
            db.commit()
    finally:
        db.close()

    # Если меняем город из меню, возвращаем на главный экран
    if data.get("menu_source") == "change_city":
        await callback.answer("✅ Miasto zostało zmienione!")
        return await show_main_menu(callback, state)

    # Иначе — сразу показываем список магазинов для выбранного региона/города
    region = data.get("region")
    stores = list_stores(region, city)

    if stores:
        rows = [[types.InlineKeyboardButton(text=s, callback_data=f"store:{s}")] for s in stores]
        rows += control_buttons()
        kb = types.InlineKeyboardMarkup(inline_keyboard=rows)

        try:
            await callback.message.edit_text(
                f"Region: {region}\nMiasto: {city}\nWybierz sklep:",
                reply_markup=kb
            )
        except TelegramBadRequest as e:
            # Игнорируем "message is not modified"
            if "message is not modified" in str(e):
                await callback.answer()
            else:
                raise

        await state.set_state(FSM.STORE)
        await callback.answer()
    else:
        # Если магазинов нет — предупредить юзера
        await callback.answer("Brak sklepów w tym mieście.", show_alert=True)
