import sqlite3
from decimal import Decimal


def adapt_decimal(d):
    return str(d)


def convert_decimal(s):
    return Decimal(s)


sqlite3.register_adapter(Decimal, adapt_decimal)
sqlite3.register_converter("DECIMAL", convert_decimal)
