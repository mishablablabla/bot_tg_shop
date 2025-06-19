from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
from bot.captcha import require_captcha
from bot.referral import require_referral
from services.user_service import user_exists, register_user
from services.store_service import list_regions, list_cities, list_stores
from services.product_service import list_products
from services.order_service import create_order
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

def main_menu_keyboard() -> types.InlineKeyboardMarkup:
    buttons = [
        [types.InlineKeyboardButton(text="1. Lokacje/Dzielnice", callback_data="menu_locations")],
        [types.InlineKeyboardButton(text="2. Praca", callback_data="menu_jobs")],
        [types.InlineKeyboardButton(text="3. Zakupy", callback_data="menu_purchases")],
        [types.InlineKeyboardButton(text="4. Zasady", callback_data="menu_rules")],
        [types.InlineKeyboardButton(text="5. Info", callback_data="menu_info")],
        [types.InlineKeyboardButton(text="6. Zmień miasto", callback_data="menu_change_city")],
        [types.InlineKeyboardButton(text="7. Opinie", callback_data="menu_reviews")],
    ]
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

async def show_main_menu(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "Witaj! Wybierz opcję:" if await state.get_state() != FSM.MAIN_MENU else "Witaj ponownie! Wybierz opcję:",
        reply_markup=main_menu_keyboard()
    )
    await state.set_state(FSM.MAIN_MENU)

@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    if user_exists(message.from_user.id):
        await message.answer("Witaj ponownie! Wybierz opcję:", reply_markup=main_menu_keyboard())
        await state.set_state(FSM.MAIN_MENU)
    else:
        await state.set_state(FSM.CAPTCHA)
        await require_captcha(message=message, state=state)

@router.message(FSM.CAPTCHA, require_captcha)
async def after_captcha(message: types.Message, state: FSMContext):
    await message.answer("Wprowadź swoje słowo kodowe:")
    await state.set_state(FSM.REFERRAL)

@router.message(FSM.REFERRAL, require_referral)
async def after_referral(message: types.Message, state: FSMContext):
    data = await state.get_data()
    register_user(message.from_user.id, data["referral_code"])
    await message.answer("Rejestracja ukończona. Wybierz opcję:", reply_markup=main_menu_keyboard())
    await state.set_state(FSM.MAIN_MENU)

@router.callback_query(FSM.MAIN_MENU)
async def main_menu_handler(callback: types.CallbackQuery, state: FSMContext):
    action = callback.data

    if action == "menu_locations":
        await state.update_data(menu_source="main_menu")
        db = SessionLocal()
        try:
            user = db.query(User).filter_by(telegram_id=callback.from_user.id).first()
            if user and user.city:
                loc = db.query(Location).filter_by(city=user.city).first()
                region = loc.region if loc else None

                await state.update_data(region=region, city=user.city)
                stores = list_stores(region, user.city)
                
                if stores:
                    rows = [[types.InlineKeyboardButton(text=s, callback_data=f"store:{s}")] for s in stores]
                    rows += control_buttons(back=True, cancel=True)
                    kb = types.InlineKeyboardMarkup(inline_keyboard=rows)
                    await callback.message.edit_text(
                        f"Zapisany region: {region}\nZapisane miasto: {user.city}\nWybierz sklep:",
                        reply_markup=kb
                    )
                    await state.set_state(FSM.STORE)
                else:
                    await callback.answer("Brak sklepów w tym mieście.", show_alert=True)
                return
        finally:
            db.close()

        regions = list_regions()
        rows = [[types.InlineKeyboardButton(text=r, callback_data=f"region:{r}")] for r in regions]
        rows += control_buttons(back=False, cancel=True)
        kb = types.InlineKeyboardMarkup(inline_keyboard=rows)
        await callback.message.edit_text("Wybierz region:", reply_markup=kb)
        await state.set_state(FSM.REGION)

    elif action == "menu_jobs":
        text = "Sekcja Praca jest w budowie."
        kb = types.InlineKeyboardMarkup(inline_keyboard=back_to_menu_button())
        await callback.message.edit_text(text, reply_markup=kb)
        await state.set_state(FSM.INFO_SCREEN)

    elif action == "menu_purchases":
        text = "Twoje zakupy:\n(Brak danych)"
        kb = types.InlineKeyboardMarkup(inline_keyboard=back_to_menu_button())
        await callback.message.edit_text(text, reply_markup=kb)
        await state.set_state(FSM.INFO_SCREEN)

    elif action == "menu_rules":
        text = (
            "Zasady:\n"
            "1. Nie sprzedajemy nielegalnych substancji.\n"
            "2. Zachowuj kulturę w rozmowach.\n"
            "3. Respektuj innych użytkowników."
        )
        kb = types.InlineKeyboardMarkup(inline_keyboard=back_to_menu_button())
        await callback.message.edit_text(text, reply_markup=kb)
        await state.set_state(FSM.INFO_SCREEN)

    elif action == "menu_info":
        text = (
            "Info:\n"
            "Silent Seller to bezpieczna platforma do zakupów.\n"
            "W razie pytań, napisz do supportu."
        )
        kb = types.InlineKeyboardMarkup(inline_keyboard=back_to_menu_button())
        await callback.message.edit_text(text, reply_markup=kb)
        await state.set_state(FSM.INFO_SCREEN)

    elif action == "menu_change_city":
        await state.update_data(menu_source="change_city")
        regions = list_regions()
        rows = [[types.InlineKeyboardButton(text=r, callback_data=f"region:{r}")] for r in regions]
        rows += control_buttons(back=True, cancel=True)
        kb = types.InlineKeyboardMarkup(inline_keyboard=rows)
        await callback.message.edit_text("Wybierz region dla nowego miasta:", reply_markup=kb)
        await state.set_state(FSM.REGION)

    elif action == "menu_reviews":
        text = "Opinie użytkowników:\n(Brak opinii)"
        kb = types.InlineKeyboardMarkup(inline_keyboard=back_to_menu_button())
        await callback.message.edit_text(text, reply_markup=kb)
        await state.set_state(FSM.INFO_SCREEN)

    else:
        await callback.answer()

@router.callback_query(lambda c: c.data.startswith("region:"))
async def choose_region(callback: types.CallbackQuery, state: FSMContext):
    region = callback.data.split(":",1)[1]
    await state.update_data(region=region)
    cities = list_cities(region)
    
    if cities:
        rows = [[types.InlineKeyboardButton(text=c, callback_data=f"city:{c}")] for c in cities]
        rows += control_buttons(back=True, cancel=True)
        kb = types.InlineKeyboardMarkup(inline_keyboard=rows)
        await callback.message.edit_text(f"Region: {region}\nWybierz miasto:", reply_markup=kb)
        await state.set_state(FSM.CITY)
    else:
        await callback.answer("Brak miast w tym regionie.", show_alert=True)
    
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("city:"))
async def choose_city(callback: types.CallbackQuery, state: FSMContext):
    city = callback.data.split(":",1)[1]
    data = await state.get_data()
    await state.update_data(city=city)

    db = SessionLocal()
    try:
        u = db.query(User).filter_by(telegram_id=callback.from_user.id).first()
        if u:
            u.city = city
            db.commit()
    finally:
        db.close()

    if data.get("menu_source") == "change_city":
        await show_main_menu(callback, state)
        await callback.answer("Miasto zostało zmienione!")
        return

    stores = list_stores(data["region"], city)
    
    if stores:
        rows = [[types.InlineKeyboardButton(text=s, callback_data=f"store:{s}")] for s in stores]
        rows += control_buttons(back=True, cancel=True)
        kb = types.InlineKeyboardMarkup(inline_keyboard=rows)
        await callback.message.edit_text(
            f"Region: {data['region']}\nMiasto: {city}\nWybierz sklep:", 
            reply_markup=kb
        )
        await state.set_state(FSM.STORE)
    else:
        await callback.answer("Brak sklepów w tym mieście.", show_alert=True)
    
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("store:"))
async def choose_store(callback: types.CallbackQuery, state: FSMContext):
    store = callback.data.split(":",1)[1]
    await state.update_data(store=store)
    data = await state.get_data()
    products = list_products(data["region"], data["city"], store)
    
    if products:
        rows = [[
            types.InlineKeyboardButton(
                text=f"{p['name']} – {p['price']} zł",
                callback_data=f"product:{p['name']}"
            )
        ] for p in products]
        rows += control_buttons(back=True, cancel=True)
        kb = types.InlineKeyboardMarkup(inline_keyboard=rows)
        await callback.message.edit_text(
            f"Region: {data['region']}\nMiasto: {data['city']}\nSklep: {store}\nWybierz produkt:",
            reply_markup=kb
        )
        await state.set_state(FSM.PRODUCT)
    else:
        await callback.answer("Brak produktów w tym sklepie.", show_alert=True)
    
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("product:"))
async def choose_product(callback: types.CallbackQuery, state: FSMContext):
    product_name = callback.data.split(":",1)[1]
    await state.update_data(product=product_name)
    data = await state.get_data()
    
    text = (
        f"Podsumowanie zamówienia:\n"
        f"Region: {data['region']}\n"
        f"Miasto: {data['city']}\n"
        f"Sklep: {data['store']}\n"
        f"Produkt: {product_name}\n\n"
        "Potwierdzasz zamówienie?"
    )
    
    rows = [
        [types.InlineKeyboardButton(text="✅ Potwierdź", callback_data="confirm")],
        *control_buttons(back=True, cancel=True)
    ]
    
    kb = types.InlineKeyboardMarkup(inline_keyboard=rows)
    await callback.message.edit_text(text, reply_markup=kb)
    await state.set_state(FSM.CONFIRM)
    await callback.answer()

@router.callback_query(lambda c: c.data == "confirm")
async def confirm_order(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    order = create_order(
        telegram_id=callback.from_user.id,
        region=data["region"],
        city=data["city"],
        store=data["store"],
        product_name=data["product"],
    )
    await callback.message.edit_text(f"Zamówienie {order.order_id} utworzone. Status: {order.status}")
    await state.clear()
    await callback.answer()

@router.callback_query(lambda c: c.data == "back")
async def go_back(callback: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    data = await state.get_data()

    if current_state == FSM.CONFIRM.state:
        await choose_store(callback, state)
    elif current_state == FSM.PRODUCT.state:
        await choose_store(callback, state)
    elif current_state == FSM.STORE.state:
        if data.get("menu_source") == "main_menu" or data.get("menu_source") == "change_city":
            await show_main_menu(callback, state)
        else:
            region = data["region"]
            cities = list_cities(region)
            if cities:
                rows = [[types.InlineKeyboardButton(text=c, callback_data=f"city:{c}")] for c in cities]
                rows += control_buttons(back=True, cancel=True)
                kb = types.InlineKeyboardMarkup(inline_keyboard=rows)
                await callback.message.edit_text(f"Region: {region}\nWybierz miasto:", reply_markup=kb)
                await state.set_state(FSM.CITY)
            else:
                await callback.answer("Brak miast w tym regionie.", show_alert=True)
    
    elif current_state == FSM.CITY.state:
        regions = list_regions()
        if regions:
            rows = [[types.InlineKeyboardButton(text=r, callback_data=f"region:{r}")] for r in regions]
            rows += control_buttons(back=True, cancel=True)
            kb = types.InlineKeyboardMarkup(inline_keyboard=rows)
            await callback.message.edit_text("Wybierz region:", reply_markup=kb)
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
    await callback.message.edit_text("Proces anulowany. Użyj /start, aby rozpocząć ponownie.")
    await callback.answer()