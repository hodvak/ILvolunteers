import datetime
from typing import Dict

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, ConversationHandler

import algorithms
import user
from services import gmap
from services.database import Database
from telegram_bot import consts

SUPPLY_TEXT = "הנה רשימת הציוד העיקרי שיש לנו, יש ללחוץ על הכפתור הרלוונטי ואז תפתח לך אפשרות להוסיף כמות"


def set_supply(user_data: Dict):
    user_data["supply"] = {
        # maybe will change
        i: 0 for i in user.Supply
    }
    user_data["supply"]["אחר"] = ""


def create_supply_keyboard(user_data: Dict):
    supply = user_data["supply"]
    buttons = [
        [
            InlineKeyboardButton(f"{key} : {value}", callback_data=key)
        ] for key, value in supply.items()
    ]
    buttons.append([InlineKeyboardButton("סיימתי", callback_data="done")])
    return InlineKeyboardMarkup(buttons)


async def supply_conv_func(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    data = update.callback_query.data
    context.user_data["choosing"] = data

    if data == "done":
        del context.user_data["choosing"]
        await update.callback_query.edit_message_text(
            "לאן להביא את הציוד? (ניתן לשלוח כתובות או מיקום)"
        )
        return consts.Convo.ADDRESS_REQUESTER
    if data == "אחר":
        await update.callback_query.edit_message_text(
            "איזה ציוד נדרש? (הודעה זאת תעבור לנציג אנושי)"
        )
        return consts.Convo.SUPPLY_OTHER_REQUESTER

    await update.callback_query.edit_message_text(
        f"כמה {data} תצטרכו?"
    )
    return consts.Convo.SUPPLY_AMOUNT_REQUESTER


async def supply_amount_conv_func(update: Update, context: ContextTypes.DEFAULT_TYPE):
    amount = update.message.text
    amount = amount.strip()
    if not amount.isdigit():
        await update.message.reply_text("הכנס מספר תקין וחיובי (או 0)")
        return consts.Convo.SUPPLY_AMOUNT_REQUESTER

    amount = int(amount)
    context.user_data["supply"][context.user_data["choosing"]] = amount
    del context.user_data["choosing"]

    await update.message.reply_text(SUPPLY_TEXT,
                                    reply_markup=create_supply_keyboard(context.user_data))

    return consts.Convo.SUPPLY_REQUESTER


async def supply_other_conv_func(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["supply"]["אחר"] = update.message.text
    await update.message.reply_text(SUPPLY_TEXT,
                                    reply_markup=create_supply_keyboard(context.user_data))
    return consts.Convo.SUPPLY_REQUESTER


async def address_conv_func(update: Update, context: ContextTypes.DEFAULT_TYPE):
    address = update.message.text
    point = (0, 0)
    if not address:
        point = (update.message.location.latitude, update.message.location.longitude)
        address = gmap.get_address(point)
    else:
        point = gmap.get_point(address)

    if not point:
        await update.message.reply_text(
            "לא הצלחתי למצוא את המיקום שהזנת, נסה שוב או שלח לי מיקום\n במקרה ואתם מסתבכים אנא שלחו הודעה ל @hodvak"
        )
        return consts.Convo.ADDRESS_REQUESTER

    context.user_data["location"] = {
        "address": address,
        "point": point
    }

    await update.message.reply_text(
        "מתי קמים מהשבעה?\n"
        "אנא שלחו בפורמט הבא:\n"
        "```dd/mm/yy```"
    )
    return consts.Convo.END_DATE_REQUESTER


async def end_date_conv_func(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date = update.message.text
    date = date.strip()
    spliters = ["/", ".", "-", " "]
    while date and any(date[0] == spliter for spliter in spliters):
        date = date[1:]
    while date and any(date[-1] == spliter for spliter in spliters):
        date = date[:-1]

    if not date:
        await update.message.reply_text(
            "אצטרך את זה בפורמט הזה ```dd/mm/yy```",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return consts.Convo.END_DATE_REQUESTER

    first, second, others = '', '', ['']
    for spliter in spliters:
        if spliter in date:
            first, second, *others = date.split(spliter)
            break

    if others:
        others = others[0]
    else:
        others = '2023'

    if not first.isdigit() or not second.isdigit() or not others.isdigit():
        await update.message.reply_text(
            "אצטרך את זה בפורמט הזה ```dd/mm/yy```",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return consts.Convo.END_DATE_REQUESTER

    day = int(first)
    month = int(second)
    year = int(others)

    if year < 100:
        year += 2000

    try:
        end_date = datetime.datetime(year, month, day)
    except:
        await update.message.reply_text(
            "אצטרך את זה בפורמט הזה ```dd/mm/yy```",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return consts.Convo.END_DATE_REQUESTER

    context.user_data["end_date"] = end_date
    await update.message.reply_text(
        "אנחנו כבר מנסים לארגן לכם את הדדברים, נעדכן כאשר נמצא"
    )
    if context.user_data["supply"]["אחר"]:
        for admin in consts.ADMINS:
            context.bot.sendMessage(
                chat_id=admin,
                text=f"הגיעה בקשה חדשה מאחד המשתמשים:\n"
                     f"שם: {context.user_data['name']}\n"
                     f"טלפון: {context.user_data['phone']}\n"
                     f"כתובת: {context.user_data['location']['address']}\n"
                     f" ציוד: {context.user_data['supply']['אחר']}\n"
            )
        del context.user_data["supply"]["אחר"]

    await Database().add_request(context.user_data)
    b = await algorithms.ask_supplier(context.user_data, context.bot)
    if not b:
        await update.message.reply_text(
            "לא הצלחנו למצוא ספקים, נחזור אליכם בהקדם עם מענה אנושי"
        )
        for admin in consts.ADMINS:
            await context.bot.sendMessage(
                chat_id=admin,
                text=f"לא הצלחנו למצוא ספקים לבקשה הבאה:\n"
                     f"שם: {context.user_data['name']}\n"
                     f"טלפון: {context.user_data['phone']}\n"
                     f"כתובת: {context.user_data['location']['address']}\n"
                     f" ציוד: {context.user_data['supply']}\n"
            )
    return ConversationHandler.END
