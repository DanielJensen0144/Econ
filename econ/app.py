from flask import Flask, redirect, render_template, request, session
from flask_session import Session
from cs50 import SQL
from econfunctions import login_required, lookup, usd, csn, graph_lookup, get_dark_mode_state, get_name
from werkzeug.security import generate_password_hash as pass_hash_gen, check_password_hash as pass_check
from datetime import datetime

#app config
app = Flask(__name__)

#session config - cookies
app.config["SESSION_PERMANENT"] = True
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

#database setup
db = SQL('sqlite:///econ.db')


# get dark mode state
@app.context_processor
def get_dark_mode_state_from_cookie():
    dark_mode_state = get_dark_mode_state(request)
    return dict(dark_mode_state=dark_mode_state)

#Remove cache with http response
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/homepage")
def homepage():
    return render_template("homepage.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    elif request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("control-password")
        
        # input control
        if not username or not password or not confirmation:
            return render_template("register.html", error="boxes", er=True)
        elif username in db.execute("SELECT username FROM users"):
            return render_template("register.html", error="username", er=True)
        
        # add user to database
        db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", username, pass_hash_gen(password))
        return render_template("homepage.html", success="TRUE")
    

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    elif request.method == "POST":
        # check username and password
        username = request.form.get("username")
        password = request.form.get("password")

        if not username:
            return render_template("login.html", error="grrr", er=True)
        elif not password:
            return render_template("login.html", error="grrr", er=True)
        
        # ensure correct username and password
        arnold = db.execute("SELECT * FROM users WHERE username = ?", username)
        if len(arnold) != 1 or not pass_check(arnold[0]["hash"], password):
            return render_template("login.html", error="sus", er=True)

        # remember which user logged in
        session["user_id"] = arnold[0]["id"]

        return redirect("/")


@app.route("/")
@login_required
def index():
    # show current stocks, cash, and total value
    id = session["user_id"]
    # check if logged in
    if not id:
        redirect("/login")

    # establish data    
    portfolio = {}
    n = 0
    cash = db.execute("SELECT cash FROM users WHERE id = ?", id)[0]["cash"]
    cash_total = cash

    for asset in db.execute("SELECT name, SUM(share_count), price FROM stocks WHERE owner_id = ? GROUP BY name", id):
        # store data in variables
        symbol = asset["name"]
        name = get_name(symbol)
        stock = lookup(symbol)
        price = stock["price"]
        shares = asset["SUM(share_count)"]
        total = shares * price
        cash_total = cash_total + total

        portfolio[n] = {"name": name, "price": usd(price), "shares": csn(shares), "total": usd(total), "symbol": symbol}
        n += 1
    
    return render_template("index.html", portfolio=portfolio, length=len(portfolio), len=len, cash_total=usd(cash_total), cash=usd(cash))


@app.route("/research", methods=["GET", "POST"])
@login_required
def research():
    if request.method == "GET":
        return render_template("research.html")
    else:
        # get symbol
        symbol = request.form.get("symbol")
        quote = lookup(symbol)
        if quote == None:
            return render_template("research.html", error="quote", er=True)
        
        # get data
        name = quote["name"]
        price = quote["price"]
        symbol = quote["symbol"]
        date = quote["date"]
        open = quote["open"]
        high = quote["high"]
        low = quote["low"]
        close = quote["close"]
        volume = quote["volume"]
        error = None
        
        
        ### display historical data
        days = request.form.get("days")
        if days == None or days.isdigit() == False:
            days = 31
            error = 'float'
        else:
            try:
                days = int(days)
            except ValueError:
                return render_template("research.html", error="float", er=True)
        if days < 7 or days > 365:
            return render_template("research.html", error="days", er=True)
            
        # collect multiple data points
        q = graph_lookup(symbol, days)
        length = len(q["q_date"])
        if q == None:
            return render_template("research.html", error="graph", er=True)
        
        # get data lists
        q_d = []
        q_h = []
        q_l = []
        q_p = []
        q_v = []

        for i in range(length):
            q_d.append(q["q_date"][i])
            q_h.append(q["q_high"][i])
            q_l.append(q["q_low"][i])
            q_p.append(q["q_adj_close"][i])
            q_v.append(q["q_volume"][i])

        # calculate stock metrics
        growth = round((q_p[0] - q_p[-1]), 2)
        growth_percentage = growth / (round((q_p[0] / 100), 2))
        growth_percentage = round(growth_percentage, 2)
        growth = growth
        growth_p2 = growth / (round((q_p[-1] / 100), 2))
        growth_p2 = round((growth_p2), 2)

        for i in range(length):
            q_h[i] = q_h[i]
            q_l[i] = q_l[i]
            q_p[i] = q_p[i]
            q_v[i] = csn(q_v[i])

        # display data
        return render_template("research.html", name=name, symbol=symbol, len=length, q_d=q_d, q_h=q_h, q_l=q_l, q_p=q_p, q_v=q_v, days=days, growth=growth, growth_p=growth_percentage, growth_p2=growth_p2, error=error, usd=usd)
    

@app.route("/buy")
@login_required
def buy():
    return render_template("buy.html")

@app.route("/confirm-b", methods=["POST"])
@login_required
def confirm_b():
    # collect data and store it semantically
    symbol = request.form.get("symbol").upper()
    if lookup(symbol) == None:
        return render_template("buy.html", error="symbol", er=True)
    shares = int(request.form.get("shares"))
    stock = lookup(symbol)
    price = stock["price"]
    total = (price * shares)
    id = session["user_id"]
    cash = db.execute("SELECT cash FROM users WHERE id = ?", id)[0]["cash"]
    name = get_name(symbol)
    if len(name) > 32:
        name = symbol

    # add stock and subtract price from user's cash
    if cash < total:
        return render_template("buy.html", error="broke", er=True)
    elif total < 1:
        return render_template("buy.html", error="hackerman", er=True)
    else:
        db.execute("UPDATE users SET cash = cash - ? WHERE id = ?", total, id)
        db.execute("INSERT INTO stocks (name, share_count, price, owner_id) VALUES (?,?,?,?)", symbol, shares, price, id)
        db.execute("DELETE FROM stocks WHERE share_count = 0 AND owner_id = ?", id)
        db.execute("INSERT INTO history (type, name, shares, price, id, time) VALUES (?,?,?,?,?,?)", "Bought", name, shares, price, id, datetime.now())
        return redirect("/")
        # return render_template("confirm_buy.html", symbol=symbol, shares=shares, price=price, total=total, cash=cash)
        
@app.route("/sell")
@login_required
def sell():
    return render_template("sell.html");

@app.route("/confirm-s", methods=["POST"])
@login_required
def confirm_s():
    # get form data
    symbol = request.form.get("symbol").upper()
    shares = int(request.form.get("shares"))
    stock = lookup(symbol)
    if lookup(symbol) == None:
        return render_template("sell.html", error=symbol, er=True)
    
    price = stock["price"]
    total = (price * shares)
    id = session["user_id"]
    share_total = db.execute("SELECT SUM(share_count) FROM stocks WHERE owner_id = ? AND name = ?", id, symbol)[0]["SUM(share_count)"]
    cash = db.execute("SELECT cash FROM users WHERE id = ?", id)[0]["cash"]
    name = get_name(symbol)
    if len(name) > 32:
        name = symbol

    # sell stock
    if not share_total or share_total < shares:
        return render_template("sell.html", error="scammer", er=True)
    elif shares < 0:
        return render_template("sell.html", error="selfscammer_or_deficitbuyer", er=True)
    else:
        db.execute("UPDATE stocks SET share_count = share_count - ? WHERE owner_id = ? AND name = ?", shares, id, symbol)
        db.execute("DELETE FROM stocks WHERE share_count = 0 AND owner_id = ?", id)
        db.execute("UPDATE users SET cash = cash + ? WHERE id = ?", total, id)
        db.execute("INSERT INTO history (type, name, shares, price, id, time) VALUES (?,?,?,?,?,?)", "Sold", name, shares, price, id, datetime.now())
        # return render_template("confirm_sell.html", symbol=symbol, shares=shares, price=price, total=total, cash=cash)
        return redirect("/")


@app.route("/history")
@login_required
def history():
    id = session["user_id"]
    history = {}
    n = 0

    user_history = db.execute("SELECT * FROM history WHERE id = ?", id)
    for data in user_history:
        # grab data
        type = data["type"]
        shares = data["shares"]
        price = data["price"]
        time = data["time"]
        name = data["name"]

        # add data to dict
        history[n] = {'type': type, 'name': name, 'shares': shares, 'price': price, 'time': time}
        n += 1

    # render history
    return render_template("history.html", history=history, len=n);

    
@app.route("/logout")
@login_required
def logout():
    # fogert user id
    session.clear()

    # redirect user to homepage
    return render_template("homepage.html", success="TRUE2")