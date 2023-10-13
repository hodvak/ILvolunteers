from typing import Optional, Tuple

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import user
from telegram_bot import supplier, requester, consts
from user import Type


def _validate_phone(phone: str) -> Optional[str]:
    phone = phone.replace("-", "").replace(" ", "")
    if phone.startswith("+972"):
        phone = '0' + phone[4:]
    if len(phone) != 10:
        return None
    if not phone.isdigit():
        return None

    return phone


async def start_conv_func(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    start the conversation, and save the user data
    next step is to choose the type of the user
    """

    context.user_data.clear()
    print(context.user_data)
    context.user_data["telegram_data"] = {
        "chat_id": update.message.chat_id,
        "username": update.message.from_user.username,
        "first_name": update.message.from_user.first_name,
        "last_name": update.message.from_user.last_name,
    }

    buttons = [
        [
            InlineKeyboardButton(text="להתנדבות לחצו כאן", callback_data=Type.DELIVER.value)
        ],
        [
            InlineKeyboardButton(text="לתרומת ציוד לחצו כאן", callback_data=Type.SUPPLIER.value),
        ],
        [
            InlineKeyboardButton(text="משפחות שכולות לחצו כאן", callback_data=Type.REQUESTER.value),
        ],
    ]
    await update.message.reply_text("במקרה שמשהו ושתבש ניתן לכתוב שוב /START או לפנות ל @hodvak")
    await update.message.reply_text("היי, אנחנו מוקד תמיכה במשפחות הנופלים ואנחנו כאן לעזור להם לעבור את ימי השבעה.",
                              reply_markup=InlineKeyboardMarkup(buttons))

    return consts.Convo.TYPE


async def type_conv_func(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    context.user_data["type"] = update.callback_query.data
    await update.callback_query.edit_message_text("דבר ראשון נצטרך טלפון של איש/אשת קשר.\n")
    return consts.Convo.PHONE


async def phone_conv_func(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.contact:
        context.user_data["phone"] = update.message.contact.phone_number
    else:
        phone = _validate_phone(update.message.text)
        if phone:
            context.user_data["phone"] = phone
        else:
            await update.message.reply_text("מספר הטלפון שהזנת לא תקין, אנא נסה שוב")
            return consts.Convo.PHONE

    # NAME #
    await update.message.reply_text("ומה השם שלו/שלה?")
    return consts.Convo.NAME


async def name_conv_func(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # todo: validate name
    if ' ' not in update.message.text:
        await update.message.reply_text("אנא הזן שם מלא בעברית")
        return consts.Convo.NAME

    context.user_data["name"] = update.message.text
    # ADDRESS #
    await update.message.reply_text("קיבלתי, תודה")
    if context.user_data["type"] == Type.DELIVER.value:
        await update.message.reply_text(
            "עיקר הצורך שלנו הוא עזרה בהקמה של אוהלים, פריסת שולחנות וכסאות והבאת ציוד נלווה למשפחות, תוכל לשלוח מיקום או כתובת בבקשה?")
        return consts.Convo.ADDRESS_DELIVER

    if context.user_data["type"] == Type.SUPPLIER.value:
        supplier.set_supply(context.user_data)
        buttons = supplier.create_supply_keyboard(context.user_data)
        await update.message.reply_text(
            supplier.SUPPLY_TEXT,
            reply_markup=buttons)

        return consts.Convo.SUPPLY_SUPPLIER

    elif context.user_data["type"] == Type.REQUESTER.value:
        requester.set_supply(context.user_data)
        buttons = requester.create_supply_keyboard(context.user_data)
        await update.message.reply_text(
            requester.SUPPLY_TEXT,
            reply_markup=buttons)

        return consts.Convo.SUPPLY_REQUESTER
