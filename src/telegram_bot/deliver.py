from typing import Dict, Literal

from bson import ObjectId
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

import algorithms
import user
from services.database import Database
from services import gmap
from telegram_bot import consts


def set_cars(user_data: Dict):
    user_data["licence"] = {
        i: False for i in user.Cars
    }
    user_data["own"] = {
        i: False for i in user.Cars
    }


def create_cars_keyboard(user_data: Dict, which: Literal["licence", "own"]):
    cars = user_data[which]
    words = {
        True: "✅",
        False: "❎"
    }
    buttons = [
        [
            InlineKeyboardButton(f"{words[value]} {key}", callback_data=key)
        ] for key, value in cars.items()
    ]

    buttons.append([InlineKeyboardButton("סיימתי", callback_data="done")])
    return InlineKeyboardMarkup(buttons)


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
        return consts.Convo.ADDRESS_DELIVER

    context.user_data["location"] = {
        "address": address,
        "point": point
    }

    await update.message.reply_text(
        "מה המרחק מקסימום בק\"מ מהעיר/כתובת ?\n(במקרה של כל הארץ יש לכתוב 1000)"
    )

    return consts.Convo.DISTANCE_DELIVER


async def distance_conv_func(update: Update, context: ContextTypes.DEFAULT_TYPE):
    distance = update.message.text
    distance = distance.strip()
    if not distance.isdigit():
        await update.message.reply_text("הכנס מספר תקין וחיובי")
        return consts.Convo.DISTANCE_DELIVER

    distance = int(distance)
    context.user_data["distance"] = distance

    set_cars(context.user_data)
    keyboard = create_cars_keyboard(context.user_data, "licence")
    await update.message.reply_text(
        "איזה **רישיון נהיגה** יש לך?\n"
        "לחיצה על הכפתור תשנה בין \"אין לי\" ל\"יש לי\"\n"
        "בסיום לחצו על כפתור \"סיימתי\""
        , reply_markup=keyboard
    )

    return consts.Convo.LICENCE_DELIVER


async def licence_conv_func(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    licence = query.data
    if licence == "done":
        keyboard = create_cars_keyboard(context.user_data, "own")
        await query.message.edit_text(
            "איזה **רכבים** יש לך?\n"
            "לחיצה על הכפתור תשנה בין \"אין לי\" ל\"יש לי\"\n"
            "בסיום לחצו על כפתור \"סיימתי\""
            , reply_markup=keyboard
        )
        return consts.Convo.VEHICLE_DELIVER
    context.user_data["licence"][licence] = not context.user_data["licence"][licence]
    keyboard = create_cars_keyboard(context.user_data, "licence")
    await query.message.edit_text(
        "איזה **רישיון נהיגה** יש לך?\n"
        "לחיצה על הכפתור תשנה בין \"אין לי\" ל\"יש לי\"\n"
        "בסיום לחצו על כפתור \"סיימתי\""
        , reply_markup=keyboard
    )

    return consts.Convo.LICENCE_DELIVER


async def vehicle_conv_func(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    vehicle = query.data
    if vehicle == "done":
        await query.message.edit_text(
            "תודה רבה, כאשר יהיה משהו שאנחנו מאמינים שתוכל לעזור בו ניצור איתך קשר שוב!"
        )
        await Database().add_user(context.user_data)
        await algorithms.ask_delivery_approval(context.user_data, context.bot)
        return ConversationHandler.END

    context.user_data["own"][vehicle] = not context.user_data["own"][vehicle]
    keyboard = create_cars_keyboard(context.user_data, "own")
    await query.message.edit_text(
        "איזה **רכבים** יש לך?\n"
        "לחיצה על הכפתור תשנה בין \"אין לי\" ל\"יש לי\"\n"
        "בסיום לחצו על כפתור \"סיימתי\""
        , reply_markup=keyboard
    )

    return consts.Convo.VEHICLE_DELIVER


async def deliver_res(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    res_id = ObjectId(query.data.split('_')[2])
    req = await Database().get_request(res_id)
    await algorithms.accept_delivery(req,
                                     update.callback_query.message.chat_id,
                                     update.callback_query.message.message_id,
                                     context.bot)


async def volunteer_res(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    res_id = ObjectId(query.data.split('_')[2])
    req = await Database().get_request(res_id)
    await algorithms.accept_volunteer(req,
                                      update.callback_query.message.chat_id,
                                      update.callback_query.message.message_id,
                                      context.bot)
