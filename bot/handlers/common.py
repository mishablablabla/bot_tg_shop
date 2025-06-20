from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest

from bot.captcha import require_captcha
from bot.referral import require_referral
from services.user_service import user_exists, register_user
from services.store_service import list_regions, list_cities, list_stores
from db.session import SessionLocal
from db.models import User, Location

router = Router()

class FSM(StatesGroup):
    CAPTCHA = State()
    REFERRAL = State()
    REGION = State()
    CITY = State()
    STORE = State()
    PRODUCT = State()
    CONFIRM = State()
    MAIN_MENU = State()
    INFO_SCREEN = State()

def control_buttons(back: bool = True, cancel: bool = True):
    row = []
    if back:
        row.append(types.InlineKeyboardButton(text="⬅️ Wróć", callback_data="back"))
    if cancel:
        row.append(types.InlineKeyboardButton(text="❌ Anuluj", callback_data="cancel"))
    return [row] if row else []

def back_to_menu_button() -> list:
    return [[types.InlineKeyboardButton(text="⬅️ Wróć", callback_data="back_to_menu")]]

def get_user_info(telegram_id: int) -> tuple:
    db = SessionLocal()
    try:
        u = db.query(User).filter_by(telegram_id=telegram_id).first()
        return telegram_id, (u.city if u else None), bool(u and u.city)
    finally:
        db.close()

def main_menu_keyboard(has_city: bool) -> types.InlineKeyboardMarkup:
    buttons = [
        [types.InlineKeyboardButton(text="📍 Lokacje/Dzielnice", callback_data="menu_locations")],
        [types.InlineKeyboardButton(text="💼 Praca", callback_data="menu_jobs")],
        [types.InlineKeyboardButton(text="🛒 Zakupy", callback_data="menu_purchases")],
        [types.InlineKeyboardButton(text="📜 Zasady", callback_data="menu_rules")],
        [types.InlineKeyboardButton(text="ℹ️ Info", callback_data="menu_info")],
        [types.InlineKeyboardButton(
            text="🔄 Zmień miasto" if has_city else "🌆 Wybierz miasto",
            callback_data="menu_change_city"
        )],
        [types.InlineKeyboardButton(text="⭐ Opinie", callback_data="menu_reviews")],
    ]
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

class FakeCallback:
    def __init__(self, data, original_callback):
        self.data = data
        self.message = original_callback.message
        self.from_user = original_callback.from_user
        self.original = original_callback

    async def answer(self, *args, **kwargs):
        return await self.original.answer(*args, **kwargs)

async def show_main_menu(message_or_callback, state: FSMContext):
    user_id = message_or_callback.from_user.id
    telegram_id, city, has_city = get_user_info(user_id)

    greeting = "Witaj w Silent Seller! 👋" if await state.get_state() != FSM.MAIN_MENU else "Witaj ponownie! 👋"
    user_info = (
        f"👤 <b>Twoje ID:</b> <code>{telegram_id}</code>\n"
        f"🌍 <b>Miasto:</b> {city or '<i>nie wybrano</i>'}"
    )
    text = f"{greeting}\n\n{user_info}\n\n👇 <b>Wybierz opcję:</b>"

    if isinstance(message_or_callback, types.Message):
        await message_or_callback.answer(text, reply_markup=main_menu_keyboard(has_city), parse_mode="HTML")
    else:
        try:
            await message_or_callback.message.edit_text(text, reply_markup=main_menu_keyboard(has_city), parse_mode="HTML")
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                await message_or_callback.answer()
            else:
                raise

    await state.set_state(FSM.MAIN_MENU)

@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    if user_exists(message.from_user.id):
        await show_main_menu(message, state)
    else:
        await state.set_state(FSM.CAPTCHA)
        await require_captcha(message=message, state=state)

@router.message(FSM.CAPTCHA, require_captcha)
async def after_captcha(message: types.Message, state: FSMContext):
    await message.answer("✏️ <b>Wprowadź swoje słowo kodowe:</b>", parse_mode="HTML")
    await state.set_state(FSM.REFERRAL)

@router.message(FSM.REFERRAL, require_referral)
async def after_referral(message: types.Message, state: FSMContext):
    data = await state.get_data()
    register_user(message.from_user.id, data["referral_code"])
    await message.answer("✅ <b>Rejestracja ukończona!</b>", parse_mode="HTML")
    await show_main_menu(message, state)


@router.callback_query(lambda c: c.data == "back")
async def go_back(callback: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    data = await state.get_data()
    from bot.handlers.order import choose_store
    from bot.handlers.location import choose_region

    if current_state == FSM.CONFIRM.state:
        store = data.get("store")
        if store:
            fake_cb = FakeCallback(f"store:{store}", callback)
            await choose_store(fake_cb, state)
        else:
            await callback.answer("Brak danych o sklepie.", show_alert=True)

    elif current_state == FSM.PRODUCT.state:
        region = data.get("region")
        city = data.get("city")
        if region and city:
            stores = list_stores(region, city)
            if stores:
                rows = [
                    [types.InlineKeyboardButton(text=s, callback_data=f"store:{s}")]
                    for s in stores
                ]
                rows += control_buttons(back=True, cancel=True)
                kb = types.InlineKeyboardMarkup(inline_keyboard=rows)
                try:
                    await callback.message.edit_text(
                        f"Region: {region}\nMiasto: {city}\nWybierz sklep:",
                        reply_markup=kb
                    )
                except TelegramBadRequest as e:
                    if "message is not modified" in str(e):
                        await callback.answer()
                    else:
                        raise
                await state.set_state(FSM.STORE)
            else:
                await callback.answer("Brak sklepów w tym mieście.", show_alert=True)
        else:
            await callback.answer("Brak danych o regionie/miście.", show_alert=True)
    elif current_state == FSM.STORE.state:
        if data.get("menu_source") in ("main_menu", "change_city"):
            await show_main_menu(callback, state)
        else:
            region = data.get("region")
            if region:
                cities = list_cities(region)
                if cities:
                    rows = [
                        [types.InlineKeyboardButton(text=c, callback_data=f"city:{c}")]
                        for c in cities
                    ]
                    rows += control_buttons(back=True, cancel=True)
                    kb = types.InlineKeyboardMarkup(inline_keyboard=rows)
                    try:
                        await callback.message.edit_text(
                            f"Region: {region}\nWybierz miasto:",
                            reply_markup=kb
                        )
                    except TelegramBadRequest as e:
                        if "message is not modified" in str(e):
                            await callback.answer()
                        else:
                            raise
                    await state.set_state(FSM.CITY)
                else:
                    await callback.answer("Brak miast w tym regionie.", show_alert=True)
            else:
                await callback.answer("Brak danych o regionie.", show_alert=True)
    elif current_state == FSM.CITY.state:
        regions = list_regions()
        if regions:
            rows = [
                [types.InlineKeyboardButton(text=r, callback_data=f"region:{r}")]
                for r in regions
            ]
            rows += control_buttons(back=True, cancel=True)
            kb = types.InlineKeyboardMarkup(inline_keyboard=rows)
            try:
                await callback.message.edit_text(
                    "Wybierz region:", reply_markup=kb
                )
            except TelegramBadRequest as e:
                if "message is not modified" in str(e):
                    await callback.answer()
                else:
                    raise
            await state.set_state(FSM.REGION)
        else:
            await callback.answer("Brak regionów.", show_alert=True)

    elif current_state == FSM.REGION.state:
        await show_main_menu(callback, state)

    elif current_state == FSM.INFO_SCREEN.state:
        await show_main_menu(callback, state)

    else:
        await callback.answer("Nie można cofnąć się dalej.")


@router.callback_query(lambda c: c.data == "back_to_menu")
async def back_to_main_menu(callback: types.CallbackQuery, state: FSMContext):
    await show_main_menu(callback, state)
    await callback.answer()

@router.callback_query(lambda c: c.data == "cancel")
async def cancel_process(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await callback.message.edit_text("❌ <b>Proces anulowany</b>\nUżyj /start, aby rozpocząć ponownie.", parse_mode="HTML")
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            await callback.answer()
        else:
            raise
    await callback.answer()
