from typing import Dict

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

from services import gmap
from services.database import Database


async def find_suppliers(user_data, not_good=()):
    suppliers = await Database().get_supplier(user_data['supply'])
    can_travel_suppliers = []
    cannot_travel_suppliers = []
    for s in suppliers:
        if s['telegram_data']['chat_id'] in not_good:
            continue
        distance = gmap.get_distance(s['location']['point'], user_data['location']['point'])
        if distance <= s['distance']:
            can_travel_suppliers.append((s, distance))
        else:
            cannot_travel_suppliers.append((s, distance))
    can_travel_suppliers.sort(key=lambda x: x[1])
    cannot_travel_suppliers.sort(key=lambda x: x[1])
    return can_travel_suppliers, cannot_travel_suppliers


async def find_volunteers(user_data):
    volunteers = await Database().get_delivery()
    good_volunteers = []
    for v in volunteers:
        distance = gmap.get_distance(v['location']['point'], user_data['location']['point'])
        if distance <= v['distance']:
            good_volunteers.append((v, distance))
    return good_volunteers


async def ask_supplier(user_data, bot: Bot, not_good=()):
    best_supp, good_supp = await find_suppliers(user_data, not_good)
    if best_supp:
        sup = best_supp[0]
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("יש לי את הציוד ואני יכול להביא",
                                     callback_data=f"sd_yy_{user_data['_id']}")
            ],
            [
                InlineKeyboardButton("יש לי את הציוד אבל צריך שמישהו יביא",
                                     callback_data=f"sd_yn_{user_data['_id']}")
            ],
            [
                InlineKeyboardButton("אין לי את הציוד",
                                     callback_data=f"sd_nn_{user_data['_id']}")
            ]
        ])
        normal_data = '\n'.join([f"{k}: {v}" for k, v in user_data['supply'].items()])

        message = await bot.send_message(sup[0]['telegram_data']['chat_id'],
                                         f"האם תוכל להביא את הציוד הבא לכתובת {user_data['location']['address']} אשר נמצאת {sup[1]:.2f} ק\"מ ממך?\n"
                                         f"{normal_data}",
                                         reply_markup=keyboard)

        await Database().send_supplier_message(user_data['_id'],
                                               sup[0]['telegram_data']['chat_id'],
                                               message.message_id)
        return True
    elif good_supp:
        sup = good_supp[0]
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("יש לי את הציוד", callback_data=f"s_y_{user_data['telegram_data']['chat_id']}")
            ],
            [
                InlineKeyboardButton("אין לי את הציוד", callback_data=f"s_n_{user_data['telegram_data']['chat_id']}")
            ]
        ])
        normal_data = '\n'.join([f"{k}: {v}" for k, v in user_data['supply'].items()])
        message = await bot.send_message(sup[0]['telegram_data']['chat_id'],
                                         f"האם יש לך את הציוד הבא?\n"
                                         f"{normal_data}",
                                         reply_markup=keyboard)
        await Database().send_supplier_message(user_data['_id'],
                                               sup[0]['telegram_data']['chat_id'],
                                               message.message_id)
        return True
    else:
        return False


async def ask_delivers(req: Dict, bot: Bot) -> bool:
    volunteers = await find_volunteers(req)
    volunteers_chat_ids = [v[0]['telegram_data']['chat_id'] for v in volunteers]
    messages_ids = []
    if not volunteers:
        return False
    for v in volunteers:
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("אני יכול להביא", callback_data=f"d_y_{req['_id']}")
            ]
        ])
        message = await bot.send_message(v[0]['telegram_data']['chat_id'],
                                         f"האם תוכל להביא את הציוד לכתובת {req['location']['address']} אשר נמצאת"
                                         f" {v[1]:.2f} ק\"מ ממך?",
                                         reply_markup=keyboard)
        messages_ids.append(message.message_id)

    await Database().send_delivery_message(req['_id'],
                                           volunteers_chat_ids,
                                           messages_ids)
    return True


async def ask_volunteers(req, bot):
    volunteers = await find_volunteers(req)
    volunteers_chat_ids = [v[0]['telegram_data']['chat_id'] for v in volunteers]
    messages_ids = []
    if not volunteers:
        return False
    for v in volunteers:
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("אני יכול לעזור", callback_data=f"v_y_{req['_id']}")
            ]
        ])
        message = await bot.send_message(v[0]['telegram_data']['chat_id'],
                                         f"תוכל להקים את הציוד בכתובת {req['location']['address']} אשר נמצאת"
                                         f" {v[1]:.2f} ק\"מ ממך?",
                                         reply_markup=keyboard)
        messages_ids.append(message.message_id)

    await Database().send_helpe_message(req['_id'],
                                        volunteers_chat_ids,
                                        messages_ids)
    return True
