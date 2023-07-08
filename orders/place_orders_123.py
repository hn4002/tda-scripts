import argparse
from datetime import datetime, timedelta
import json
import os
import pytz
import requests
import sys
import traceback
import urllib3

from tda import auth, client

from tda.orders.common import (
    StopPriceLinkBasis,
    Destination,
    Session,
    OrderStrategyType,
    ComplexOrderStrategyType,
    PriceLinkBasis,
    StopPriceLinkType,
    PriceLinkType,
    one_cancels_other,
    Duration,
    EquityInstruction,
    first_triggers_second,
    StopType,
    OrderType
)
from tda.orders.generic import OrderBuilder

from setenv import tdaSettings


#
# API Documentation:
# * https://tda-api.readthedocs.io/en/latest/
# * https://developer.tdameritrade.com/apis
#

token_path = tdaSettings.TDA_TOKEN_PATH
api_key = tdaSettings.TDA_APIKEY
redirect_uri = tdaSettings.TDA_REDIRECT_URI
account_id = tdaSettings.TDA_ACCOUNT_ID

#=====================================================================================
def place_order(order):
    print("Initializing TDA client...")
    tda_client = auth.client_from_token_file(token_path, api_key)
    print(f"TDA Client: Calling place order for account_id = {account_id}, order = {order}")
    r = tda_client.place_order(account_id, order)
    print(f"TDA Client: status_code = {r.status_code}")
    assert (r.status_code == 200 or r.status_code == 201), r.raise_for_status()
    print(json.dumps(r.json(), indent=4))

#=====================================================================================
def prepare_order_long(symbol, buy_shares, buy_stop_price, sellbr1_shares, sellbr1_limit_price, sellbr1_stop_price,
                     sellbr2_shares, sellbr2_limit_price, sellbr2_stop_price,
                     sellbr3_shares, sellbr3_limit_price, sellbr3_stop_price):
    (entry_order) = (OrderBuilder()
        .set_order_strategy_type(OrderStrategyType.TRIGGER)
        .set_session(Session.NORMAL)
        .set_duration(Duration.DAY)
        .set_order_type(OrderType.STOP)
        .copy_stop_price(buy_stop_price)
        .add_equity_leg(EquityInstruction.BUY, symbol, buy_shares))

    (exit_order_1A) = (OrderBuilder()
            .set_order_strategy_type(OrderStrategyType.SINGLE)
            .set_session(Session.NORMAL)
            .set_duration(Duration.GOOD_TILL_CANCEL)
            .set_order_type(OrderType.LIMIT)
            .set_price(sellbr1_limit_price)
            .add_equity_leg(EquityInstruction.SELL, symbol, sellbr1_shares))
    (exit_order_1B) = (OrderBuilder()
            .set_order_strategy_type(OrderStrategyType.SINGLE)
            .set_session(Session.NORMAL)
            .set_duration(Duration.GOOD_TILL_CANCEL)
            .set_order_type(OrderType.STOP)
            .copy_stop_price(sellbr1_stop_price)
            .add_equity_leg(EquityInstruction.SELL, symbol, sellbr1_shares))

    (exit_order_2A) = (OrderBuilder()
            .set_order_strategy_type(OrderStrategyType.SINGLE)
            .set_session(Session.NORMAL)
            .set_duration(Duration.GOOD_TILL_CANCEL)
            .set_order_type(OrderType.LIMIT)
            .set_price(sellbr2_limit_price)
            .add_equity_leg(EquityInstruction.SELL, symbol, sellbr2_shares))
    (exit_order_2B) = (OrderBuilder()
            .set_order_strategy_type(OrderStrategyType.SINGLE)
            .set_session(Session.NORMAL)
            .set_duration(Duration.GOOD_TILL_CANCEL)
            .set_order_type(OrderType.STOP)
            .copy_stop_price(sellbr2_stop_price)
            .add_equity_leg(EquityInstruction.SELL, symbol, sellbr2_shares))

    (exit_order_3A) = (OrderBuilder()
            .set_order_strategy_type(OrderStrategyType.SINGLE)
            .set_session(Session.NORMAL)
            .set_duration(Duration.GOOD_TILL_CANCEL)
            .set_order_type(OrderType.LIMIT)
            .set_price(sellbr3_limit_price)
            .add_equity_leg(EquityInstruction.SELL, symbol, sellbr3_shares))
    (exit_order_3B) = (OrderBuilder()
            .set_order_strategy_type(OrderStrategyType.SINGLE)
            .set_session(Session.NORMAL)
            .set_duration(Duration.GOOD_TILL_CANCEL)
            .set_order_type(OrderType.STOP)
            .copy_stop_price(sellbr3_stop_price)
            .add_equity_leg(EquityInstruction.SELL, symbol, sellbr3_shares))

    exit_order_1OCO = one_cancels_other(exit_order_1A,  exit_order_1B) # Creates a new order
    exit_order_2OCO = one_cancels_other(exit_order_2A,  exit_order_2B) # Creates a new order
    exit_order_3OCO = one_cancels_other(exit_order_3A,  exit_order_3B) # Creates a new order

    entry_order.set_order_strategy_type(OrderStrategyType.TRIGGER) \
        .add_child_order_strategy(exit_order_1OCO) \
        .add_child_order_strategy(exit_order_2OCO) \
        .add_child_order_strategy(exit_order_3OCO)

    return entry_order

#=====================================================================================
def main():
    print("Started")

    # Update this for every position
    symbol = "AMD"
    buyPrice = 101.00
    stoplossPrice = 100.00

    # Global parameters
    maxRiskPerPos = 50

    R = buyPrice - stoplossPrice
    shares = round(maxRiskPerPos / R)

    print (f"symbol = {symbol}")
    print (f"shares = {shares}")
    print (f"buyPrice = {buyPrice}")
    print (f"stoplossPrice = {stoplossPrice}")

    pg1R = buyPrice + 1 * R
    pg2R = buyPrice + 2 * R
    pg3R = buyPrice + 3 * R
    br1_shares = int(shares / 3)
    br2_shares = int(shares / 3)
    br3_shares = shares - br1_shares - br2_shares


    order = prepare_order_long(symbol, shares, buyPrice,
                     br1_shares, pg1R, stoplossPrice,
                     br2_shares, pg2R, stoplossPrice,
                     br3_shares, pg3R, stoplossPrice)


    print(f"Order object created. Order = {order}")

    # TODO: Uncomment this to send the order to the broker.
    # By default, this is disabled for account protection.
    #place_order(order)

    print("Finished")

#=====================================================================================
if __name__ == "__main__":
    main()

