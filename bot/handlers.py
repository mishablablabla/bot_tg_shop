from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest
from bot.captcha import require_captcha
from bot.referral import require_referral
from services.user_service import user_exists, register_user
from services.store_service import list_regions, list_cities, list_stores
from services.product_service import list_products
from services.order_service import create_order
from db.session import SessionLocal
from db.models import User, Location, Product

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
    """Возвращает (telegram_id, город, есть ли город)"""
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(telegram_id=telegram_id).first()
        city = user.city if user else None
        return telegram_id, city, bool(city)
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
    """Имитация callback для возврата в предыдущее состояние"""
    def __init__(self, data, original_callback):
        self.data = data
        self.message = original_callback.message
        self.from_user = original_callback.from_user
        self.original = original_callback
        
    async def answer(self, *args, **kwargs):
        """Проксируем вызов answer к оригинальному callback"""
        return await self.original.answer(*args, **kwargs)

async def show_main_menu(message_or_callback: types.Message | types.CallbackQuery, state: FSMContext):
    user_id = message_or_callback.from_user.id
    telegram_id, city, has_city = get_user_info(user_id)
    
    user_info = (
        f"👤 <b>Twój ID:</b> <code>{telegram_id}</code>\n"
        f"🌍 <b>Miasto:</b> {city if city else '<i>nie wybrano</i>'}"
    )
    
    is_welcome = await state.get_state() != FSM.MAIN_MENU
    greeting = "Witaj w Silent Seller! 👋" if is_welcome else "Witaj ponownie! 👋"
    
    text = f"{greeting}\n\n{user_info}\n\n👇 <b>Wybierz opcję:</b>"
    
    if isinstance(message_or_callback, types.Message):
        await message_or_callback.answer(
            text, 
            reply_markup=main_menu_keyboard(has_city),
            parse_mode="HTML"
        )
    else:
        try:
            await message_or_callback.message.edit_text(
                text,
                reply_markup=main_menu_keyboard(has_city),
                parse_mode="HTML"
            )
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
                    try:
                        await callback.message.edit_text(
                            f"Zapisany region: {region}\nZapisane miasto: {user.city}\nWybierz sklep:",
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
                return
        finally:
            db.close()

        regions = list_regions()
        rows = [[types.InlineKeyboardButton(text=r, callback_data=f"region:{r}")] for r in regions]
        rows += control_buttons(back=False, cancel=True)
        kb = types.InlineKeyboardMarkup(inline_keyboard=rows)
        try:
            await callback.message.edit_text("Wybierz region:", reply_markup=kb)
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                await callback.answer()
            else:
                raise
        await state.set_state(FSM.REGION)

    elif action == "menu_jobs":
        text = (
            "🚨 Szukamy ludzi do zadań specjalnych — <b>czysta robota, szybki zysk</b> 💰💨\n"
            "Zostań <b>kurierem radości</b>, <b>nocnym dostawcą śmiechu</b> albo <b>koordynatorem karuzeli emocji</b>.\n\n"
            "<b>‼️ Praca wyłącznie na kaucję – dokumenty nas nie interesują.</b>\n"
            "Masz plecak, powerbank i nerwy z tytanu?\n"
            "👉 Pisz do menedżera: @manager_nick\n\n"
            "🌙 Zakres działań:\n"
            "– nocne spacery z konkretnym celem\n"
            "– dostarczanie radości tam, gdzie szaro\n"
            "– działanie w systemie \"zrób i zniknij\"\n\n"
            "💉 Mile widziana znajomość topografii miasta i umiejętność \"niezwracania uwagi\".\n\n"
            "👉 Menedżer: @manager_nick\n\n"
        )
        kb = types.InlineKeyboardMarkup(inline_keyboard=back_to_menu_button())
        try:
            await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                await callback.answer()
            else:
                raise
        await state.set_state(FSM.INFO_SCREEN)

    elif action == "menu_purchases":
        text = "Twoje zakupy:\n(Brak danych)"
        kb = types.InlineKeyboardMarkup(inline_keyboard=back_to_menu_button())
        try:
            await callback.message.edit_text(text, reply_markup=kb)
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                await callback.answer()
            else:
                raise
        await state.set_state(FSM.INFO_SCREEN)

    elif action == "menu_rules":
        text = (
            "📜 <b>Zasady gry — przeczytaj, zanim wskoczysz w ten biznes:</b>\n\n"
            "🔐 <b>Dyskrecja to twój najlepszy kumpel:</b>\n"
            "– Zero nazw, zero szczegółów. Tu nie sprzedają lemoniady, więc pytania zostaw sobie na podwórko.\n"
            "– Korzystaj z kont bez twarzy i historii — nikt nie musi wiedzieć, kim jesteś.\n"
            "– Screensy, lokalizacje i rozmowy w sieci? Zapomnij. Internet to po prostu wielki Big Brother.\n\n"
            "📦 <b>Jak odebrać zakładkę — instrukcja mistrza:</b>\n"
            "1. Zapłać i nie marudź, bo nie przyjmujemy negocjacji.\n"
            "2. Dostaniesz dokładne koordynaty i zdjęcie punktu — to twój GPS do szczęścia.\n"
            "3. Idź sam, bez gapiów i selfie-sticków.\n"
            "4. Sprawdź miejsce, działaj szybko, jak ninja na mieście.\n"
            "5. Odebrałeś? Usuń czat i wyczyść ślady — ślady zostawiamy tylko na ulicy.\n"
            "6. Telefon w tryb ninja — nie chcemy dzwonków na posterunku.\n\n"
            "🕳️ <b>Nie widzisz zakładki? Spokojnie, co robić:</b>\n"
            "– Zrób kilka zdjęć miejsca z różnych kątów — niech będzie dowód, że szukałeś.\n"
            "– Prześlij lokalizację i opis problemu — załatwimy, żebyś nie biegał bez sensu.\n"
            "– Spokój i opanowanie — nie bawimy się w akcje z filmu sensacyjnego.\n\n"
            "👉 Menedżer: @manager_nick\n\n"
            "⚠️ <b>Pamiętaj — to nie jest gra na luzie:</b>\n"
            "– Myśl jak szef — głowa do góry, problemów mniej.\n"
            "– Kamery i obserwatorzy są wszędzie — więc zachowuj się jak duch.\n"
            "– Zakładka nie zniknie, ale ty możesz, jeśli nie będziesz ogarnięty.\n\n"
            "😎 <i>Wchodzisz, odbierasz, znikasz — bez hałasu i bez ściemy.</i>"
        )
        kb = types.InlineKeyboardMarkup(inline_keyboard=back_to_menu_button())
        try:
            await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                await callback.answer()
            else:
                raise
        await state.set_state(FSM.INFO_SCREEN)

    elif action == "menu_info":
        text = (
            "ℹ️ Silent Seller — co tu i jak?\n\n"
            "Tu jest prosto: chcesz — bierzesz, chcesz — znikasz.\n"
            "Bot to twój cichy pomocnik w świecie, gdzie każdy krok waży złoto.\n\n"
            "• Wybierz miasto (jeśli jeszcze tego nie zrobiłeś).\n"
            "• Przejdź do „Lokacje”, wybierz swój region.\n"
            "• Wybierz towar, zapłać, odbierz i zniknij.\n\n"
            "• Płatności tylko przez "
            "<a href=\"https://t.me/cryptobot\">@CryptoBot</a> — bezpieczny sposób zapłacić za wszystko, nawet za swoje szczęście 😉\n\n"
            "• Bezpieczeństwo ponad wszystko\n"
            "Zero zbędnych słów, żadnych śladów. Usuń czaty, nie świeć się, nie pal punktów.\n\n"
            "• Jak korzystać\n"
            "Wybierz towar, czekaj na koordynaty, odbierz szybko i dyskretnie.\n"
            "Usuń wiadomości — to ważne, ziomek.\n\n"
            "• Dbamy o naszych klientów\n"
            "Bo my tu nie tylko o towar chodzi, ale i o to, żebyś Ty nie wpadł.\n"
            "Stracić klienta przez głupotę? Nie w naszym stylu — więc bądź sprytny i trzymaj się zasad.\n\n"
            "• Wsparcie\n"
            "Jeśli coś — pisz, ale bez paniki i dramatu. Wszystko załatwimy cicho.\n\n"
            "👉 Menedżer: @manager_nick\n\n"
            "• Pamiętaj\n"
            "Nikt tu nie chce problemów. Dyskrecja to twoja zbroja. Bądź mądrzejszy od innych."
        )
        kb = types.InlineKeyboardMarkup(inline_keyboard=back_to_menu_button())
        try:
            await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML", disable_web_page_preview=True)
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                await callback.answer()
            else:
                raise
        await state.set_state(FSM.INFO_SCREEN)

    elif action == "menu_change_city":
        await state.update_data(menu_source="change_city")
        regions = list_regions()
        rows = [[types.InlineKeyboardButton(text=r, callback_data=f"region:{r}")] for r in regions]
        rows += control_buttons(back=True, cancel=True)
        kb = types.InlineKeyboardMarkup(inline_keyboard=rows)
        try:
            await callback.message.edit_text("Wybierz region dla nowego miasta:", reply_markup=kb)
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                await callback.answer()
            else:
                raise
        await state.set_state(FSM.REGION)

    elif action == "menu_reviews":
        text = "Opinie użytkowników:\n(Brak opinii)"
        kb = types.InlineKeyboardMarkup(inline_keyboard=back_to_menu_button())
        try:
            await callback.message.edit_text(text, reply_markup=kb)
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                await callback.answer()
            else:
                raise
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
        try:
            await callback.message.edit_text(f"Region: {region}\nWybierz miasto:", reply_markup=kb)
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                await callback.answer()
            else:
                raise
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
        await callback.answer("✅ Miasto zostało zmienione!")
        await show_main_menu(callback, state)
        return

    stores = list_stores(data["region"], city)
    
    if stores:
        rows = [[types.InlineKeyboardButton(text=s, callback_data=f"store:{s}")] for s in stores]
        rows += control_buttons(back=True, cancel=True)
        kb = types.InlineKeyboardMarkup(inline_keyboard=rows)
        try:
            await callback.message.edit_text(
                f"Region: {data['region']}\nMiasto: {city}\nWybierz sklep:", 
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
        try:
            await callback.message.edit_text(
                f"Region: {data['region']}\nMiasto: {data['city']}\nSklep: {store}\nWybierz produkt:",
                reply_markup=kb
            )
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                await callback.answer()
            else:
                raise
        await state.set_state(FSM.PRODUCT)
    else:
        await callback.answer("Brak produktów w tym sklepie.", show_alert=True)
    
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("product:"))
async def choose_product(callback: types.CallbackQuery, state: FSMContext):
    product_name = callback.data.split(":",1)[1]
    await state.update_data(product=product_name)
    data = await state.get_data()

    db = SessionLocal()
    try:
        product = db.query(Product).filter_by(name=product_name).first()
        description = product.description if product else "Brak opisu"
    finally:
        db.close()

    text = (
        f"<b>Podsumowanie zamówienia:</b>\n"
        f"▫️ Region: {data['region']}\n"
        f"▫️ Miasto: {data['city']}\n"
        f"▫️ Sklep: {data['store']}\n"
        f"▫️ Produkt: {product_name}\n"
        f"▫️ Opis: {description}\n\n"
        "Potwierdzasz zamówienie?"
    )
    
    rows = [
        [types.InlineKeyboardButton(text="✅ Potwierdź", callback_data="confirm")],
        *control_buttons(back=True, cancel=True)
    ]
    
    kb = types.InlineKeyboardMarkup(inline_keyboard=rows)
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            await callback.answer()
        else:
            raise
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
    try:
        await callback.message.edit_text(
            f"✅ <b>Zamówienie utworzone!</b>\n"
            f"ID: <code>{order.order_id}</code>\n"
            f"Status: {order.status}",
            parse_mode="HTML"
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            await callback.answer()
        else:
            raise
    await state.clear()
    await callback.answer()

@router.callback_query(lambda c: c.data == "back")
async def go_back(callback: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    data = await state.get_data()

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