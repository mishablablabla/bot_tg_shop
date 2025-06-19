import random
from aiogram import types, F
from aiogram.filters import BaseFilter
from aiogram.fsm.context import FSMContext
from config import settings

class CaptchaFilter(BaseFilter):
    async def __call__(self, message: types.Message, state: FSMContext):
        data = await state.get_data()
        if "captcha" not in data:
            a = random.randint(1, 9)
            b = random.randint(1, 9)
            op = random.choice(settings.CAPTCHA_OPERATIONS)
            expr = f"{a}{op}{b}"
            answer = eval(expr)
            await state.update_data(captcha={"expr": expr, "ans": str(answer)})
            await message.answer(f"Captcha: {expr} = ?")
            return False
        else:
            if message.text.strip() == data["captcha"]["ans"]:
                await state.update_data(captcha_passed=True)
                return True
            else:
                await message.answer("Wrong captcha. Try again.")
                del data["captcha"]
                await state.clear()
                return False

require_captcha = CaptchaFilter()
