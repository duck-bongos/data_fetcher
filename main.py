import csv
import configparser
from typing import Dict
import asyncio

import uvloop

import alpaca_retrieval as ar

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


def setup(fname: str = "config.ini") -> Dict[str, str]:
    config = configparser.ConfigParser()
    config.read(fname)

    return {
        "API-KEY": config["DEFAULT"]["API-KEY"],
        "API-SECRET": config["DEFAULT"]["API-SECRET"],
    }


if __name__ in "__main__":
    fname_ticker = "SP500.csv"
    with open(fname_ticker) as ft:
        reader = csv.DictReader(ft)
        tickers = [row["Symbol"].strip().rstrip() for row in reader]

    config = setup()
    rq = ar.make_async_requests(
        tickers, config=config, timeframe="3M", start="2023-12-25T09:40:36.485824Z"
    )
    asyncio.run(ar.co_query_alpaca(rq))
