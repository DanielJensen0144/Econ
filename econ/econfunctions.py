from flask import session, redirect
from pytz import timezone
import datetime
import urllib
from uuid import uuid4
from requests import get as rget, RequestException
import csv
from functools import wraps
import yfinance as yf


def login_required(f):
    # direct the user to the homepage until they have logged in
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/homepage")
        return f(*args, **kwargs)
    return decorated_function
    

def usd(bread):
    # format the bread correctly with commas and a dollar sign
    return f"${bread:,.2f}"

def csn(bread):
    # return the comma seperated number
    bread = int(bread)
    return f"{bread:,.0f}"
        

def get_name(symbol):
    try:
        yfinance = "https://query2.finance.yahoo.com/v1/finance/search"
        user_agent = "python-requests"
        params = {"q": symbol, "quotes_count": 1}

        res = rget(url=yfinance, params=params, headers={'User-Agent': user_agent})
        data = res.json()

        name = data['quotes'][0]['shortname']
        return name
    except KeyError:
        try:
            yfinance = "https://query2.finance.yahoo.com/v1/finance/search"
            user_agent = "python-requests"
            params = {"q": symbol, "quotes_count": 1}

            res = rget(url=yfinance, params=params, headers={'User-Agent': user_agent})
            data = res.json()

            name = data['quotes'][0]['longname']
            return name
        except KeyError:
            return symbol


def lookup(symbol):
    # capitalize symbol
    symbol = symbol.upper()

    # prepare API request
    end = datetime.datetime.now(timezone("Europe/Copenhagen"))
    start = end - datetime.timedelta(days=7)

    # download data from yahoo finance
    url = (
        f"https://query1.finance.yahoo.com/v7/finance/download/{urllib.parse.quote_plus(symbol)}"
        f"?period1={int(start.timestamp())}"
        f"&period2={int(end.timestamp())}"
        f"&interval=1d&events=history&includeAdjustedClose=true"
    )

    try:
        res = rget(url, cookies={"session": str(uuid4())}, headers={"User-Agent": "python-requests", "Accept": "*/*"})
        res.raise_for_status()

        # add data to table
        quote = list(csv.DictReader(res.content.decode("UTF-8").splitlines()))
        quote.reverse()
        date = quote[0]["Date"]
        name = get_name(symbol)
        open = round(float(quote[0]["Close"]), 2)
        high = round(float(quote[0]["High"]), 2)
        low = round(float(quote[0]["Low"]), 2)
        close = round(float(quote[0]["Close"]), 2)
        adj_close = round(float(quote[0]["Adj Close"]), 2)
        volume = quote[0]["Volume"]
        return {
            "symbol": symbol,
            "price": adj_close,
            "name": name,
            "date": date,
            "open": open,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume
        }
    except (RequestException, ValueError, KeyError, IndexError):
        return None
    
def graph_lookup(symbol, days):
    # capitalize symbol
    symbol = symbol.upper()

    # prepare API request
    end = datetime.datetime.now(timezone("Europe/Copenhagen"))
    start = end - datetime.timedelta(days)

    # download data from yahoo finance
    url = (
        f"https://query1.finance.yahoo.com/v7/finance/download/{urllib.parse.quote_plus(symbol)}"
        f"?period1={int(start.timestamp())}"
        f"&period2={int(end.timestamp())}"
        f"&interval=1d&events=history&includeAdjustedClose=true"
    )

    try:
        res = rget(url, cookies={"session": str(uuid4())}, headers={"User-Agent": "python-requests", "Accept": "*/*"})
        res.raise_for_status()

        # add data to table
        q = list(csv.DictReader(res.content.decode("UTF-8").splitlines()))
        q.reverse()
        
        q_date = []
        q_open = []
        q_high = []
        q_low = []
        q_close = []
        q_adj_close = []
        q_volume = []

        for s in range(len(q)):
            q_date.append(q[s]["Date"])
            q_open.append(round(float(q[s]["Close"]), 2))
            q_high.append(round(float(q[s]["High"]), 2))
            q_low.append(round(float(q[s]["Low"]), 2))
            q_close.append(round(float(q[s]["Close"]), 2))
            q_adj_close.append(round(float(q[s]["Adj Close"]), 2))
            q_volume.append(q[s]["Volume"])

        return {
            "q_date": q_date,
            "q_open": q_open,
            "q_high": q_high,
            "q_low": q_low,
            "q_close": q_close,
            "q_adj_close": q_adj_close,
            "q_volume": q_volume
        }


    except (RequestException, ValueError, KeyError, IndexError):
        return None

        # RequestException, ValueError, KeyError, IndexError

def get_dark_mode_state(request):
    dark_mode = request.cookies.get("darkMode")
    return dark_mode == "true"