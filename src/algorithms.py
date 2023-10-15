import asyncio
from typing import Dict

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

from services import gmap
from services.database import Database
from telegram_bot import consts


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
        normal_data = '\n'.join(f"{k}: {v}" for k, v in user_data['supply'].items() if v != 0)

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
    supplier = await Database().get_user(req['supplier'])
    messages_ids = []
    supply_as_text = '\n'.join(f"{key}: {value}" for key, value in req['supply'].items() if value != 0)

    if not volunteers:
        return False
    for v in volunteers:
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("אני יכול להביא", callback_data=f"d_y_{req['_id']}")
            ]
        ])
        supplier_distance = gmap.get_distance(v[0]['location']['point'], req['location']['point'])
        message = await bot.send_message(v[0]['telegram_data']['chat_id'],
                                         f"תוכל להביא את הציוד מ{supplier['location']['address']} אשר נמצאת"
                                         f" {supplier_distance:.2f} ק\"מ ממך ל{req['location']['address']} אשר נמצאת"
                                         f" {v[1]:.2f} ק\"מ ממך? הציוד:\n"
                                         f"{supply_as_text}"
                                         ,
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


async def accept_supplier(req: Dict, supplier_chat_id: int, message_id: int, bot: Bot):
    # set the supplier of the request
    await Database().set_supplier(req['_id'], supplier_chat_id)

    # delete the message
    await bot.delete_message(supplier_chat_id, message_id)

    # send message to the supplier with the data
    supply_as_text = '\n'.join([f"{key}: {value}" for key, value in req['supply'].items() if value != 0])
    await bot.send_message(
        chat_id=supplier_chat_id,
        text=f"תודה שהבאת לנו את הציוד הבא:\n{supply_as_text}\n"
             f"נשלח לך הודעה ברגע שנדע שבאים המתנדבים לקחת ממך את הציוד\n"
    )
    await bot.send_location(
        chat_id=supplier_chat_id,
        latitude=req['location']['point'][0],
        longitude=req['location']['point'][1]
    )
    req = await Database().get_request(req['_id'])
    b = await ask_delivers(req, bot)
    if not b:
        for admin in consts.ADMINS:
            await bot.send_message(
                chat_id=admin,
                text=f"לא מצאנו שליחים לבקשה"
                     f"id: {req['_id']}"
                     f"name: {req['name']}"
                     f"phone: {req['phone']}"
                     f"location: {req['location']}"
                     f"supply: \n{supply_as_text}"
            )


async def decline_supplier(req: Dict, supplier_chat_id: int, message_id: int, bot: Bot):
    await bot.edit_message_text(
        chat_id=supplier_chat_id,
        message_id=message_id,
        text="תודה רבה בכל מקרה, אנחנו נמשיך לשלוח לכם הודעות כשנצטרך ציוד"
    )
    supply_as_text = '\n'.join([f"{key}: {value}" for key, value in req['supply'].items() if value != 0])

    supp = req['supplier_messages']
    b = await ask_supplier(req, bot, not_good=supp)
    if not b:
        for admin in consts.ADMINS:
            await bot.send_message(
                chat_id=admin,
                text=f"לא מצאנו ציוד לבקשה"
                     f"id: {req['_id']}"
                     f"name: {req['name']}"
                     f"phone: {req['phone']}"
                     f"location: {req['location']['address']}"
                     f"supply: \n{supply_as_text}"
            )


async def accept_supplier_delivery(req: Dict, supplier_chat_id: int, message_id: int, bot: Bot):
    # set the supplier and delivery of the request
    await Database().set_supplier(req['_id'], supplier_chat_id)
    await Database().set_delivery(req['_id'], supplier_chat_id)

    # delete the message
    await bot.delete_message(supplier_chat_id, message_id)
    # send message to the supplier with the data
    supply_as_text = '\n'.join([f"{key}: {value}" for key, value in req['supply'].items() if value != 0])
    await bot.send_message(
        chat_id=supplier_chat_id,
        text=f"תודה שהבאת לנו את הציוד הבא גם תיקח אותו לכתובת {req['location']['address']}:\n{supply_as_text}\n"
    )
    await bot.send_location(
        chat_id=supplier_chat_id,
        latitude=req['location']['point'][0],
        longitude=req['location']['point'][1]
    )
    req = await Database().get_request(req['_id'])
    b = await ask_volunteers(req, bot)
    if not b:
        for admin in consts.ADMINS:
            await bot.send_message(
                chat_id=admin,
                text=f"לא מצאנו שליחים לבקשה"
                     f"id: {req['_id']}"
                     f"name: {req['name']}"
                     f"phone: {req['phone']}"
                     f"location: {req['location']['address']}"
                     f"supply: \n{supply_as_text}"
            )


async def accept_delivery(req: Dict, delivery_chat_id: int, message_id: int, bot: Bot):
    # set the delivery of the request
    await Database().set_delivery(req['_id'], delivery_chat_id)
    supplier = await Database().get_user(req['supplier'])

    # delete the message for all the optional deliveries
    for data in req['delivery_messages']:
        await bot.delete_message(data['chat_id'], data['message_id'])

    # send message to the delivery with the data
    supply_as_text = '\n'.join([f"{key}: {value}" for key, value in req['supply'].items() if value != 0])
    await bot.send_message(
        chat_id=delivery_chat_id,
        text=f"תודה שהתנדבת לקחת את הציוד הבא:\n{supply_as_text}\n"
             f"מהמקום:\n"
             f"{supplier['location']['address']}\n"
             f"טלפון:\n"
             f"{supplier['phone']}\n"
             f"למקום:\n"
             f"{req['location']['address']}\n"
             f"טלפון:\n"
             f"{req['phone']}\n"
             f"תוכל ליצור איתנו קשר לעוד פרטים - @hodvak\n"
    )
    await bot.send_location(
        chat_id=delivery_chat_id,
        latitude=req['location']['point'][0],
        longitude=req['location']['point'][1]
    )
    await bot.send_location(
        chat_id=delivery_chat_id,
        latitude=supplier['location']['point'][0],
        longitude=supplier['location']['point'][1]
    )

    # send message to the supplier with the data
    await bot.send_message(
        chat_id=supplier['telegram_data']['chat_id'],
        text=f"מישהו אישר שהוא יקח את הציוד!\n"
    )

    b = await ask_volunteers(req, bot)
    if not b:
        for admin in consts.ADMINS:
            await bot.send_message(
                chat_id=admin,
                text=f"לא מצאנו מתנדבים לבקשה"
                     f"id: {req['_id']}"
                     f"name: {req['name']}"
                     f"phone: {req['phone']}"
                     f"location: {req['location']['address']}"
                     f"supply: \n{supply_as_text}"
            )


async def accept_volunteer(req: Dict, volunteer_chat_id: int, message_id: int, bot: Bot):
    # set the delivery of the request
    await Database().set_helper(req['_id'], volunteer_chat_id)

    # delete the message for all the optional deliveries
    for data in req['helper_messages']:
        await bot.delete_message(data['chat_id'], data['message_id'])

    # send message to the delivery with the data
    await bot.send_message(
        chat_id=volunteer_chat_id,
        text=f"תודה שהתנדבת לסדר את הציוד במיקום: {req['location']['address']}\n"
    )
    await bot.send_location(
        chat_id=volunteer_chat_id,
        latitude=req['location']['point'][0],
        longitude=req['location']['point'][1]
    )

    # send message to the supplier with the data
    await bot.send_message(
        chat_id=req['telegram_data']['chat_id'],
        text=f"מישהו אישר שהוא יעזור לסדר את הציוד!\n"
    )


async def send_to_admins(message: str, bot: Bot):
    messages_to_wait = [bot.send_message(
        chat_id=admin,
        text=message
    ) for admin in consts.ADMINS]
    await asyncio.gather(*messages_to_wait)
