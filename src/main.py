"""
state telegram bot
"""
import os
import logging
from enum import Enum, auto

from telegram import ForceReply, Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, ConversationHandler, \
    CallbackQueryHandler

from src.user import Type, Supply
from src.telegram_bot import consts, all, supplier, deliver, requester

TOKEN = os.environ.get("TOKEN")

conversation_handler = ConversationHandler(
    entry_points=[CommandHandler("start", all.start_conv_func)],
    states={
        # all
        consts.Convo.TYPE: [CallbackQueryHandler(all.type_conv_func)],
        consts.Convo.PHONE: [MessageHandler(filters=filters.TEXT | filters.CONTACT, callback=all.phone_conv_func)],
        consts.Convo.NAME: [MessageHandler(filters=filters.TEXT, callback=all.name_conv_func)],

        # supplier
        consts.Convo.SUPPLY_SUPPLIER: [CallbackQueryHandler(supplier.supply_conv_func)],
        consts.Convo.SUPPLY_AMOUNT_SUPPLIER: [MessageHandler(filters=filters.TEXT,
                                                             callback=supplier.supply_amount_conv_func)],
        consts.Convo.ADDRESS_SUPPLIER: [MessageHandler(filters=filters.TEXT | filters.LOCATION,
                                                       callback=supplier.supply_address_conv_func)],

        consts.Convo.DISTANCE_SUPPLIER: [MessageHandler(filters=filters.TEXT,
                                                        callback=supplier.supply_distance_conv_func)],

        # delivery
        consts.Convo.ADDRESS_DELIVER: [MessageHandler(filters=filters.TEXT | filters.LOCATION,
                                                      callback=deliver.address_conv_func)],
        consts.Convo.DISTANCE_DELIVER: [MessageHandler(filters=filters.TEXT,
                                                       callback=deliver.distance_conv_func)],
        consts.Convo.LICENCE_DELIVER: [CallbackQueryHandler(deliver.licence_conv_func)],
        consts.Convo.VEHICLE_DELIVER: [CallbackQueryHandler(deliver.vehicle_conv_func)],

        # requester
        consts.Convo.SUPPLY_REQUESTER: [CallbackQueryHandler(requester.supply_conv_func)],
        consts.Convo.SUPPLY_AMOUNT_REQUESTER: [MessageHandler(filters=filters.TEXT,
                                                              callback=requester.supply_amount_conv_func)],
        consts.Convo.SUPPLY_OTHER_REQUESTER: [MessageHandler(filters=filters.TEXT,
                                                            callback=requester.supply_other_conv_func)],
        consts.Convo.ADDRESS_REQUESTER: [MessageHandler(filters=filters.TEXT | filters.LOCATION,
                                                        callback=requester.address_conv_func)],
        consts.Convo.END_DATE_REQUESTER: [MessageHandler(filters=filters.TEXT,
                                                         callback=requester.end_date_conv_func)],

    },
    fallbacks=[CommandHandler("start", all.start_conv_func)]
)


def main() -> None:
    """Start the bot."""
    application = Application.builder().token(TOKEN).build()

    application.add_handler(conversation_handler)

    application.add_handler(CallbackQueryHandler(pattern=r"^sd?_", callback=supplier.supplier_res))
    application.add_handler(CallbackQueryHandler(pattern=r"^d_", callback=deliver.deliver_res))
    application.add_handler(CallbackQueryHandler(pattern=r"^v_", callback=deliver.volunteer_res))
    # application.add_handler(MessageHandler(filters=filters.LOCATION, callback=loc_handler))

    # application.add_handler(CommandHandler("help", help_command))
    #
    # application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
