from typing import Dict

from bson import ObjectId
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
import user
import algorithms
from services.database import Database
from services import gmap
from telegram_bot import consts

SUPPLY_TEXT = "הנה רשימת הציוד העיקרי הדרוש לנו, יש ללחוץ על הכפתור הרלוונטי ואז תפתח לך אפשרות להוסיף כמות?"


def set_supply(user_data: Dict):
    user_data["supply"] = {
        i: 0 for i in user.Supply
    }


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
            "מהו מיקום המחסן שלך? (ניתן לשלוח כתובות או מיקום)"
        )
        return consts.Convo.ADDRESS_SUPPLIER

    await update.callback_query.edit_message_text(
        f"כמה {data} ברשותך?"
    )
    return consts.Convo.SUPPLY_AMOUNT_SUPPLIER


async def supply_amount_conv_func(update: Update, context: ContextTypes.DEFAULT_TYPE):
    number = update.message.text
    number = number.strip()
    if not number.isdigit():
        await update.message.reply_text("הכנס מספר תקין וחיובי (או 0)")
        return consts.Convo.SUPPLY_AMOUNT_SUPPLIER

    number = int(number)
    context.user_data["supply"][context.user_data["choosing"]] = number
    del context.user_data["choosing"]

    await update.message.reply_text(SUPPLY_TEXT,
                                    reply_markup=create_supply_keyboard(context.user_data))

    return consts.Convo.SUPPLY_SUPPLIER


async def supply_address_conv_func(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        return consts.Convo.ADDRESS_SUPPLIER

    context.user_data["location"] = {
        "address": address,
        "point": point
    }

    await update.message.reply_text(
        "מה המרחק בק\"מ אליו באפשרותך להביא את הציוד? (אם אין באפשרותך יש לרשום 0 במקרה של כל הארץ יש לכתוב 1000)"
    )
    return consts.Convo.DISTANCE_SUPPLIER


async def supply_distance_conv_func(update: Update, context: ContextTypes.DEFAULT_TYPE):
    distance = update.message.text
    distance = distance.strip()
    if not distance.isdigit():
        await update.message.reply_text("הכנס מספר תקין וחיובי (או 0)")
        return consts.Convo.DISTANCE_SUPPLIER

    distance = int(distance)
    context.user_data["distance"] = distance

    await update.message.reply_text(
        "תודה רבה על הציוד, נשלח הודעה כאשר נצטרך אותו"
    )
    context.user_data["start_supply"] = context.user_data["supply"]
    await Database().add_user(context.user_data)
    return ConversationHandler.END


async def supplier_res(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    data = update.callback_query.data
    data = data.split("_")
    req_id = ObjectId(data[2])
    data = data[1]
    req = await Database().get_request(req_id)
    if data == "yy":
        await algorithms.accept_supplier_delivery(req,
                                                  update.callback_query.message.chat_id,
                                                  update.callback_query.message.message_id,
                                                  context.bot)
    elif data[0] == 'y':
        await algorithms.accept_supplier(req,
                                         update.callback_query.message.chat_id,
                                         update.callback_query.message.message_id,
                                         context.bot)
    else:
        await algorithms.decline_supplier(req,
                                          update.callback_query.message.chat_id,
                                          update.callback_query.message.message_id,
                                          context.bot)
