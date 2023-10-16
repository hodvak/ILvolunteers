from bson import ObjectId
from telegram import Update
from telegram.ext import ContextTypes

import algorithms
from services.database import Database
from telegram_bot import consts


async def approve_supplier(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    data = update.callback_query.data
    data = data.split("_")
    object_id = ObjectId(data[2])
    ans = consts.APPROVAL(data[1])
    user = await Database().db.users.find_one({"_id": object_id})
    await algorithms.approve_supplier(user,
                                      update.callback_query.message.chat_id,
                                      context.bot,
                                      ans)


async def approve_delivery(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    data = update.callback_query.data
    data = data.split("_")
    object_id = ObjectId(data[2])
    ans = consts.APPROVAL(data[1])
    user = await Database().db.users.find_one({"_id": object_id})
    await algorithms.approve_delivery(user,
                                      update.callback_query.message.chat_id,
                                      context.bot,
                                      ans)


async def approve_req(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    data = update.callback_query.data
    data = data.split("_")
    object_id = ObjectId(data[2])
    ans = consts.APPROVAL(data[1])
    req = await Database().db.requests.find_one({"_id": object_id})
    await algorithms.approve_req(req,
                                 update.callback_query.message.chat_id,
                                 context.bot,
                                 ans)
