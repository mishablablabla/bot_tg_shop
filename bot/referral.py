from aiogram import types
from aiogram.filters import BaseFilter
from aiogram.fsm.context import FSMContext
from services.user_service import is_valid_code

class ReferralFilter(BaseFilter):
    async def __call__(self, message: types.Message, state: FSMContext):
        code = message.text.strip()
        if is_valid_code(code):
            await state.update_data(referral_code=code)
            return True
        await message.answer("Invalid code. Send it again.")
        return False

require_referral = ReferralFilter()
