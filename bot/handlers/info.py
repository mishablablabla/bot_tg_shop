from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from bot.handlers.common import FSM, back_to_menu_button

router = Router()

@router.callback_query(FSM.MAIN_MENU, lambda c: c.data == "menu_jobs")
async def menu_jobs(callback: types.CallbackQuery, state: FSMContext):
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

@router.callback_query(FSM.MAIN_MENU, lambda c: c.data == "menu_purchases")
async def menu_purchases(callback: types.CallbackQuery, state: FSMContext):
    kb = types.InlineKeyboardMarkup(inline_keyboard=back_to_menu_button())
    await callback.message.edit_text("Twoje zakupy:\n(Brak danych)", reply_markup=kb)
    await state.set_state(FSM.INFO_SCREEN)

@router.callback_query(FSM.MAIN_MENU, lambda c: c.data == "menu_rules")
async def menu_rules(callback: types.CallbackQuery, state: FSMContext):
    rules_text = (
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
    await callback.message.edit_text(rules_text, reply_markup=kb, parse_mode="HTML")
    await state.set_state(FSM.INFO_SCREEN)

@router.callback_query(FSM.MAIN_MENU, lambda c: c.data == "menu_info")
async def menu_info(callback: types.CallbackQuery, state: FSMContext):
    info_text = (
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
    await callback.message.edit_text(info_text, reply_markup=kb, parse_mode="HTML", disable_web_page_preview=True)
    await state.set_state(FSM.INFO_SCREEN)

@router.callback_query(FSM.MAIN_MENU, lambda c: c.data == "menu_reviews")
async def menu_reviews(callback: types.CallbackQuery, state: FSMContext):
    kb = types.InlineKeyboardMarkup(inline_keyboard=back_to_menu_button())
    await callback.message.edit_text("Opinie użytkowników:\n(Brak opinii)", reply_markup=kb)
    await state.set_state(FSM.INFO_SCREEN)
