import math

from flask import Flask
from flask import request

from datetime import datetime
from db import create_lift_pass_db_connection

# In this solution I tried to apply the imperative shell, functional core pattern
# To make it more interesting, it is not allowed to execute both requests to DB before invoking
# the whole business logic - imagine the second request is costly and should be executed only when necessary

# IMPERATIVE SHELL - side effects allowed - invokes business logic

app = Flask("lift-pass-pricing")

connection_options = {
    "host": 'localhost',
    "user": 'root',
    "database": 'lift_pass',
    "password": 'mysql'}

connection = None


@app.route("/prices", methods=['GET', 'PUT'])
def prices():
    age = request.args.get('age', type=int, default=None)
    type = request.args.get("type", default=None)
    date = datetime.fromisoformat(request.args["date"]) if "date" in request.args else None

    res = {}
    global connection
    if connection is None:
        connection = create_lift_pass_db_connection(connection_options)
    if request.method == 'PUT':
        return add_pass(connection)
    elif request.method == 'GET':
        result = get_pass(connection)
        base_price = result['cost']
        full_cost, can_have_date_discount = get_full_cost(type, base_price, age)
        if can_have_date_discount:
            is_holiday  = is_holiday_date(connection, date)
            res['cost'] = apply_date_discount(full_cost, date, is_holiday)
        else:
            res['cost'] = full_cost
    return res

def is_holiday_date(connection, date):
    if not date:
        return False
    cursor = connection.cursor()
    cursor.execute(f"SELECT * FROM holidays where holiday='{date.strftime('%Y-%m-%d')}'")
    return cursor.rowcount > 0


def get_pass(connection):
    cursor = connection.cursor()
    cursor.execute(
        'SELECT cost FROM base_price ' + 'WHERE type = ? ',
        (request.args['type'],),
    )
    row = cursor.fetchone()
    return {"cost": row[0]}


def add_pass(connection):
    lift_pass_cost = request.args["cost"]
    lift_pass_type = request.args["type"]
    cursor = connection.cursor()
    cursor.execute('INSERT INTO `base_price` (type, cost) VALUES (?, ?) ' +
                   'ON DUPLICATE KEY UPDATE cost = ?', (lift_pass_type, lift_pass_cost, lift_pass_cost))
    return {}


# FUNCTIONAL CORE - business logic - pure functions only

def get_age_discount(age):
    match age:
        case None:
            discount = 1
        case age if age < 15:
            discount = 0.7
        case age if age > 64:
            discount = .75
        case _:
            discount = 1
    return discount

def get_full_cost(type, base_price, age) -> (int, bool):
    if age and age < 6:
        return 0, False
    if not type or type == "night":
        return get_price_without_discount(age, base_price), False
    age_discount = get_age_discount(age)
    return base_price * age_discount, True

def apply_date_discount(cost, date, is_holiday):
    is_monday = date and date.weekday() == 0
    date_discount = 35 if is_monday and not is_holiday else 0
    return math.ceil(cost * (1 - date_discount / 100))

def get_price_without_discount(age, full_cost):
    match age:
        case age if age > 64:
            return math.ceil(full_cost * .4)
        case age if age >= 6:
            return full_cost
        case _:
            return 0

if __name__ == "__main__":
    app.run(port=3005)
