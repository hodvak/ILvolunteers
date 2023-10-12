from enum import Enum


class Type(str, Enum):
    SUPPLIER = "supplier"
    DELIVER = "deliver"
    REQUESTER = "requester"


class Supply(str, Enum):
    CHAIR = "כסאות"
    TABLE = "שולחנות"
    HOTWATER = "מיחמים"
    BLOCKER = "מחסומים"
    TENT = "אוהלים"


class Cars(str, Enum):
    BIKE = "אופנוע"
    CAR = "רכב פרטי"
    MINIBUS = "אוטובוס זעיר"
    BUS = "אוטובוס"
    OVER12 = "משא מעל 12 טון"
    TO12 = "משא עד 12 טון"


class Status(str, Enum):
    PENDING_SUPPLIER = "pending_supplier"
    PENDING_DELIVER = "pending_deliver"
    PENDING_VOLUNTEER = "pending_volunteer"
    IN_PROGRESS = "in_progress"
    DONE = "done"
