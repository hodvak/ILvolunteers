"""
general telegram bot functions (for all the users types)
"""
from enum import Enum, auto
from typing import List, Optional, Callable, Dict


class Convo(Enum):
    # ALL
    START = auto()
    TYPE = auto()
    PHONE = auto()
    NAME = auto()

    # SUPPLIER
    SUPPLY_SUPPLIER = auto()
    SUPPLY_AMOUNT_SUPPLIER = auto()
    ADDRESS_SUPPLIER = auto()
    DISTANCE_SUPPLIER = auto()

    # DELIVERY
    ADDRESS_DELIVER = auto()
    DISTANCE_DELIVER = auto()
    LICENCE_DELIVER = auto()
    VEHICLE_DELIVER = auto()

    # REQUESTER
    SUPPLY_REQUESTER = auto()
    SUPPLY_AMOUNT_REQUESTER = auto()
    SUPPLY_OTHER_REQUESTER = auto()
    ADDRESS_REQUESTER = auto()
    END_DATE_REQUESTER = auto()

    # END
    END = auto()

    # DEFAULT
    DEFAULT = auto()


ADMINS = []
with open("admins.txt", "r") as f:
    for line in f:
        line = line.strip()
        if line[0] == "#":
            continue
        ADMINS.append(int(line.strip()))
