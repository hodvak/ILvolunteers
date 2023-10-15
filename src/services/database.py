import asyncio
from datetime import datetime, timezone
from os import environ
from pprint import pprint
from typing import Optional, AsyncIterable, List, Dict

import motor.motor_asyncio as motor
from bson import ObjectId
from pymongo.errors import ConnectionFailure
from user import Type, Supply, Status

HOST = environ.get('MONGO_URL') or 'mongodb://localhost:27017'
DATABASE_NAME = environ.get('DATABASE_NAME') or 'database'


class Database:
    def __init__(self):
        """
        connect to the database
        """
        try:
            self.client = motor.AsyncIOMotorClient(HOST)
        except ConnectionFailure as e:
            print("Server not available")
            raise e
        self.db = self.client[DATABASE_NAME]

    async def add_user(self, user_data: dict) -> None:
        """
        add a new user to the database
        :param user_data: the user to add
        :return: None
        """
        print(user_data)
        # check if exists by the user_data['telegram_data.chat_id']['chat_id']
        # user = await self.db.users.find_one({'telegram_data.chat_id': user_data['telegram_data']['chat_id']})
        # if user:
        #     await self.db.users.update_one({'telegram_data.chat_id': user_data['telegram_data']['chat_id']},
        #                                    user_data)
        # else:
        #     await self.db.users.insert_one(user_data)

        # delete the user if exists and insert the new one
        await self.db.users.delete_many({'telegram_data.chat_id': user_data['telegram_data']['chat_id']})
        await self.db.users.insert_one(user_data)

    async def add_request(self, user_data) -> ObjectId:
        user_data['time'] = datetime.now(timezone.utc)

        user_data['supplier'] = None
        user_data['delivery'] = None
        user_data['helper'] = []

        user_data['supplier_messages'] = []
        user_data['delivery_messages'] = []
        user_data['helper_messages'] = []

        user_data['status'] = Status.PENDING_SUPPLIER
        ans = await self.db.requests.insert_one(user_data)
        return ans.inserted_id

    async def send_supplier_message(self, request_id: ObjectId, supplier_chat_id: int, message_id: int) -> None:
        await self.db.requests.update_one({'_id': request_id},
                                          {'$push': {'supplier_messages': {'chat_id': supplier_chat_id,
                                                                           'message_id': message_id}}})

    async def send_delivery_message(self, req_id: ObjectId, delivery_chat_ids: List[int],
                                    message_ids: List[int]) -> None:
        data = [{'chat_id': chat_id, 'message_id': message_id} for chat_id, message_id in
                zip(delivery_chat_ids, message_ids)]

        await self.db.requests.update_one({'_id': req_id},
                                          {'$set': {'delivery_messages': data}})

    async def send_helpe_message(self, req_id, volunteers_chat_ids, messages_ids):
        data = [{'chat_id': chat_id, 'message_id': message_id} for chat_id, message_id in
                zip(volunteers_chat_ids, messages_ids)]

        await self.db.requests.update_one({'_id': req_id},
                                          {'$set': {'helper_messages': data}})

    async def set_supplier(self, request_id: ObjectId, supplier_chat_id: int) -> None:
        await self.db.requests.update_one(
            {'_id': request_id, 'status': Status.PENDING_SUPPLIER.value},
            {'$set': {'supplier': supplier_chat_id, 'status': Status.PENDING_DELIVER.value}})

        request = await self.db.requests.find_one({'_id': request_id})
        supply_dict = {}
        print(request['supply'])
        for name, amount in request['supply'].items():
            if name != 'אחר':
                supply_dict['supply.' + name] = -amount

        await self.db.user.update_one({'telegram_data.chat_id': supplier_chat_id},
                                      {'$inc': supply_dict})

    async def set_delivery(self, request_id: ObjectId, delivery_chat_id: int) -> None:
        await self.db.requests.update_one(
            {'_id': request_id, 'status': Status.PENDING_DELIVER.value},
            {'$set': {'delivery': delivery_chat_id, 'status': Status.PENDING_VOLUNTEER.value}})

    async def set_helper(self, request_id: ObjectId, helper_chat_id: int):
        req = await self.db.requests.find_one({'_id': request_id})
        if helper_chat_id in req['helper']:
            return
        req['helper'].append(helper_chat_id)
        if len(req['helper']) == 2:
            req['status'] = Status.IN_PROGRESS.value
        await self.db.requests.update_one({'_id': request_id}, {'$set': req})
        return req['helper']

    # async def set_done_requests(self, request_chat_id):
    #     await self.db.requests.update_one(
    #         {'telegram_data.chat_id': request_chat_id, 'status': Status.IN_PROGRESS.value},
    #         {'$set': {'status': Status.DONE.value}})
    #     req = await self.db.requests.find_one({'telegram_data.chat_id': request_chat_id})
    #     supply_dict = {}
    #     for name, amount in req['supply'].items():
    #         supply_dict['supply.' + name] = amount
    #
    #     await self.db.user.update_one({'telegram_data.chat_id': req['supplier']},
    #                                   {'$inc': supply_dict})

    async def get_supplier(self, needed_supply: Dict[Supply, int]):
        """
        get a supplier that can supply the needed supplies
        :param needed_supply: the needed supplies
        :return: the supplier
        """
        supply_dict = {}
        for name, amount in needed_supply.items():
            if name != 'אחר':
                supply_dict['supply.' + name] = {'$gte': amount}

        my_filter = {'type': Type.SUPPLIER.value, **supply_dict}
        supplier = await self.db.users.find(my_filter).to_list(length=None)
        return supplier

    async def get_delivery(self):
        return await self.db.users.find({'type': Type.DELIVER.value}).to_list(length=None)

    async def get_request(self, request_id: ObjectId):
        return await self.db.requests.find_one({'_id': request_id})

    async def set_volunteer(self, request_chat_id, volunteer_chat_id):
        await self.db.requests.update_one(
            {'telegram_data.chat_id': request_chat_id, 'status': Status.PENDING_DELIVER.value},
            {'$set': {'volunteer': volunteer_chat_id, 'status': Status.IN_PROGRESS.value}})

    async def get_user(self, chat_id):
        return await self.db.users.find_one({'telegram_data.chat_id': chat_id})
