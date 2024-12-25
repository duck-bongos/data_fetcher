from asyncio import Queue as AQueue
import configparser
from typing import Union, Dict, List, Optional
import asyncio
import uvloop
import aiohttp
from queue import Queue
from pydantic import BaseModel
import requests
from copy import copy
from datetime import datetime
import logging

logging.basicConfig(level=logging.DEBUG)
LOGGER = logging.getLogger(__name__)


class Request(BaseModel):
    url: str
    headers: Dict[str, str]
    params: Optional[Dict[str, str]] = None


asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

Q = Queue()
RQ = Queue()


def setup(fname: str = "config.ini") -> Dict[str, str]:
    config = configparser.ConfigParser()
    config.read(fname)

    return {
        "API-KEY": config["DEFAULT"]["API-KEY"],
        "API-SECRET": config["DEFAULT"]["API-SECRET"],
    }


def make_async_requests(
    symbols: Union[str, List[str]],
    config: Dict[str, str],
    timeframe: str = "5Min",
    start: str = "2019-01-25T00:00:00Z",
    end: str = "2024-12-01T00:00:00Z",
    limit: int = 10000,
    **kwargs,
) -> AQueue[Request]:
    _start = start.replace(":", "%3A")
    _end = end.replace(":", "%3A")
    if isinstance(symbols, list) and len(symbols) == 1:
        # desired type
        pass

    if isinstance(symbols, str):
        symbols = [symbols]

    elif isinstance(symbols, list) and len(symbols) > 1 and kwargs.get("bulk"):
        symbols = "%2C".join(symbols)

    # YAGNI parametrize this.
    url = (
        "https://data.alpaca.markets/v2/stocks/bars?symbols=!SYMBOLS!"
        "&timeframe=!TIMEFRAME!&start=!START!&end=!END!&limit=!LIMIT!"
        "&adjustment=raw&feed=sip&sort=asc"
    )

    _url = url.replace("!TIMEFRAME!", timeframe)
    _url = _url.replace("!START!", _start)
    _url = _url.replace("!END!", _end)
    _url = _url.replace("!LIMIT!", str(limit))

    headers = {
        "accept": "application/json",
        "APCA-API-KEY-ID": config["API-KEY"],
        "APCA-API-SECRET-KEY": config["API-SECRET"],
    }

    q = Queue()
    if kwargs.get("bulk"):
        _prep_url = _url.replace(symbols)
        req = Request(url=_prep_url, headers=headers)
        q.put(req)

    else:
        for symbol in symbols:
            _prep_url = copy(_url)
            _prep_url = _prep_url.replace("!SYMBOLS!", symbol)
            req = Request(url=_prep_url, headers=headers)
            q.put(req)

    print(f"Async Request size: {q.qsize()}")
    return q


async def co_query_alpaca(
    request_queue: Queue[Request],
    **kwargs,
):
    done_q = AQueue()
    retry_q = AQueue()
    error_q = AQueue()
    a_lock = asyncio.Lock()
    _time_when_429 = datetime.now()
    _got_429 = False
    _curr_429: datetime
    _prev_429 = datetime.now()
    # _most_recent_put = datetime(1970)
    _timeout = 5

    # conver to asyncio queue
    request_q = AQueue()
    while not request_queue.empty():
        item = request_queue.get()
        request_q.put_nowait(item)

    async with aiohttp.ClientSession() as session:
        while not request_q.empty() or not retry_q.empty():
            if not request_q.empty():
                req = await request_q.get()

            else:
                req = await retry_q.get()

            _params = req.params or {}
            async with session.get(
                url=req.url, headers=req.headers, params=_params
            ) as response:
                if response.status == 200:
                    resp = await response.json()

                    if resp.get("next_page_token"):
                        _req = Request(
                            url=req.url,
                            headers=req.headers,
                            params={"page_token": resp.get("next_page_token")},
                        )
                        await request_q.put(_req)
                        LOGGER.info(
                            "[ %s ] Adding to request_q, now has %s items",
                            str(response.status),
                            str(request_q.qsize()),
                        )

                    await done_q.put(resp["bars"])

                elif response.status == 429:
                    resp = await response.json()
                    await retry_q.put(req)

                    async with a_lock:
                        _got_429 = True
                        _curr_429 = datetime.now()

                else:
                    LOGGER.warning("[ {} ] ".format(response.status))
                    resp = await response.json()
                    await error_q.put(resp)

            async with a_lock:
                if _got_429:
                    _got_429 = False
                    # need to cool off for timeout - (most recent 429 - previous 429)
                    _delta = (_curr_429 - _prev_429).seconds / 60000
                    _cool_off_time = _timeout - _delta

                    LOGGER.warning(
                        "Whoaaa way too many requests. "
                        "Free tier is 250/min. Cooling off for %s seconds",
                        _cool_off_time,
                    )
                    _prev_429 = _curr_429
                    await asyncio.sleep(_cool_off_time)
                    # time.sleep(_cool_off_time)
                    _got_429 = False

            LOGGER.info(
                "\n[ QSizes ]\n%s\nRequests: %s\nDone: %s\nRetry: %s\nError: %s",
                "-" * len("[ QSizes ]"),
                str(request_q.qsize()),
                str(done_q.qsize()),
                str(retry_q.qsize()),
                str(error_q.qsize()),
            )


def query_alpaca(
    symbols: Union[str, List[str]],
    config: Dict[str, str],
    timeframe: str = "5Min",
    start: str = "2019-01-25T00:00:00Z",
    end: str = "2024-12-01T00:00:00Z",
    limit: int = 10000,
    **kwargs,
):
    """Query Alpaca Markets Bars API with the following info.

    Please refer to https://docs.alpaca.markets/reference/stockbars for more
    information on the paramaters.

    Args:
        symbols (Union[str, List[str]]): _description_
        config (Dict[str, str]): _description_
        timeframe (str, optional): _description_. Defaults to "5Min".
        start (_type_, optional): _description_. Defaults to "2019-01-25T00:00:00Z".
        end (_type_, optional): _description_. Defaults to "2024-12-01T00:00:00Z".
        limit (int, optional): _description_. Defaults to 10000.

    Raises:
        ValueError: _description_
    """
    _start = start.replace(":", "%3A")
    _end = end.replace(":", "%3A")
    if isinstance(symbols, list) and len(symbols) == 1:
        symbols = symbols[0]

    elif isinstance(symbols, list) and len(symbols) > 1 and kwargs.get("bulk"):
        symbols = "%2C".join(symbols)

    url = (
        "https://data.alpaca.markets/v2/stocks/bars?symbols=!SYMBOLS!"
        "&timeframe=!TIMEFRAME!&start=!START!&end=!END!&limit=!LIMIT!"
        "&adjustment=raw&feed=sip&sort=asc"
    )

    _url = url.replace("!SYMBOLS!", symbols)
    _url = _url.replace("!TIMEFRAME!", timeframe)
    _url = _url.replace("!START!", _start)
    _url = _url.replace("!END!", _end)
    _url = _url.replace("!LIMIT!", str(limit))

    headers = {
        "accept": "application/json",
        "APCA-API-KEY-ID": config["API-KEY"],
        "APCA-API-SECRET-KEY": config["API-SECRET"],
    }

    response = requests.get(_url, headers=headers)

    resp = {}
    if response.status_code == 200:
        resp = response.json()
        Q.put(resp["bars"])

    params = {}
    while not RQ.empty() or resp.get("next_page_token"):
        if not RQ.empty():
            params = RQ.get()

        else:
            params["page_token"] = resp.get("next_page_token")

        response = requests.get(_url, headers=headers, params=params)

        if response.status_code == 200:
            resp = response.json()
            Q.put(resp["bars"])
            print(f"Qsize: {Q.qsize()}")

        elif response.status_code == 429:
            RQ.put(params)
            print(f"Retry Qsize: {RQ.qsize()}")

        else:
            raise ValueError(f"unexpected event: {response}")

    print(response.text)
