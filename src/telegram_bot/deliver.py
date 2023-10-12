from typing import Dict, Literal

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

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
        "איזה רישיון נהיגה יש לך?\n"
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
            "איזה רכבים יש לך?\n"
            "לחיצה על הכפתור תשנה בין \"אין לי\" ל\"יש לי\"\n"
            "בסיום לחצו על כפתור \"סיימתי\""
            , reply_markup=keyboard
        )
        return consts.Convo.VEHICLE_DELIVER
    context.user_data["licence"][licence] = not context.user_data["licence"][licence]
    keyboard = create_cars_keyboard(context.user_data, "licence")
    await query.message.edit_text(
        "איזה רישיון נהיגה יש לך?\n"
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
        return ConversationHandler.END

    context.user_data["own"][vehicle] = not context.user_data["own"][vehicle]
    keyboard = create_cars_keyboard(context.user_data, "own")
    await query.message.edit_text(
        "איזה רכבים יש לך?\n"
        "לחיצה על הכפתור תשנה בין \"אין לי\" ל\"יש לי\"\n"
        "בסיום לחצו על כפתור \"סיימתי\""
        , reply_markup=keyboard
    )

    return consts.Convo.VEHICLE_DELIVER


async def deliver_res(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    res_chat_id = query.data.split('_')[2]
    req = await Database().get_request(res_chat_id)
    await Database().set_delivery(res_chat_id, update.callback_query.message.chat_id)
    supplier = await Database().get_user(update.callback_query.message.chat_id)
    for data in req['delivery_messages']:
        await context.bot.edit_message_text(
            chat_id=data['chat_id'],
            message_id=data['message_id'],
            text=f"מישהו אישר שהוא יקח את הציוד!\n"
                 f"תודה רבה לכולם"
        )
    await query.message.edit_reply_markup(reply_markup=None)
    await query.message.reply_text(
        f"תודה רבה שהתנדבת לקחת את הציוד!\n"
    )
    await context.bot.send_message(
        chat_id=req['telegram_data']['chat_id'],
        text=f"מישהו אישר שהוא יקח את הציוד!\n"
    )


async def volunteer_res(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    res_chat_id = query.data.split('_')[2]
    req = await Database().get_request(res_chat_id)
    await Database().set_volunteer(res_chat_id, update.callback_query.message.chat_id)
    for data in req['volunteer_messages']:
        await context.bot.edit_message_text(
            chat_id=data['chat_id'],
            message_id=data['message_id'],
            text=f"מישהו אישר שהוא יעזור לסדר את הציוד!\n"
        )
    await query.message.edit_reply_markup(reply_markup=None)
    await query.message.reply_text(
        f"תודה רבה שהתנדבת לסדר את הציוד במיקום: {req['location']['address']}\n"
    )
    await context.bot.sendLocation(
        chat_id=update.callback_query.message.chat_id,
        latitude=req['location']['point'][0],
        longitude=req['location']['point'][1]
    )
    await context.bot.send_message(
        chat_id=req['telegram_data']['chat_id'],
        text=f"מישהו אישר שהוא יעזור לסדר את הציוד!\n"
    )
