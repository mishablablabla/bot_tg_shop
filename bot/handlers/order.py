from aiogram import Router, types
from aiogram.fsm.context import FSMContext

from services.store_service import list_stores
from services.product_service import list_products
from services.order_service import create_order
from db.session import SessionLocal
from db.models import Product
from bot.handlers.common import FSM, control_buttons
from aiogram.exceptions import TelegramBadRequest

router = Router()

@router.callback_query(FSM.STORE, lambda c: c.data.startswith("store:"))
async def choose_store(callback: types.CallbackQuery, state: FSMContext):
    store = callback.data.split(":", 1)[1]
    await state.update_data(store=store)
    data = await state.get_data()

    products = list_products(data["region"], data["city"], store)
    if not products:
        await callback.answer("Brak produktów w tym sklepie.", show_alert=True)
        return

    rows = [
        [types.InlineKeyboardButton(text=f"{p['name']} – {p['price']} zł", callback_data=f"product:{p['name']}")]
        for p in products
    ]
    rows += control_buttons()

    kb = types.InlineKeyboardMarkup(inline_keyboard=rows)
    try:
        await callback.message.edit_text(
            f"Region: {data['region']}\n"
            f"Miasto: {data['city']}\n"
            f"Sklep: {store}\n"
            "Wybierz produkt:",
            reply_markup=kb
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            await callback.answer()
        else:
            raise

    await state.set_state(FSM.PRODUCT)
    await callback.answer()


@router.callback_query(FSM.PRODUCT, lambda c: c.data.startswith("product:"))
async def choose_product(callback: types.CallbackQuery, state: FSMContext):
    product_name = callback.data.split(":", 1)[1]
    await state.update_data(product=product_name)
    data = await state.get_data()

    db = SessionLocal()
    try:
        prod = db.query(Product).filter_by(name=product_name).first()
        description = prod.description if prod else "Brak opisu"
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
        *control_buttons()
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


@router.callback_query(FSM.CONFIRM, lambda c: c.data == "confirm")
async def confirm_order(callback: types.CallbackQuery, state: FSMContext):
    """
    После подтверждения — создаём заказ и показываем результат.
    """
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

