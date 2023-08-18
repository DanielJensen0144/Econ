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
        cash_total += total

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
        # the BTC-USD error is a yahoo thing, not a graph_lookup thing
        if q == None:
            return render_template("research.html", error="graph", er=True)
        length = len(q["q_date"])
        
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
    

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "GET":
        return render_template("buy.html")
    else:
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
        elif shares < 0:
            return render_template("buy.html", error="hackerman", er=True)
        elif shares == 0:
            return render_template("buy.html", error="no_shares", er=True)
        else:
            db.execute("UPDATE users SET cash = cash - ? WHERE id = ?", total, id)
            db.execute("INSERT INTO stocks (name, share_count, price, owner_id) VALUES (?,?,?,?)", symbol, shares, price, id)
            # Merge the shares into one variable
            if len(db.execute("SELECT share_count FROM stocks WHERE name = ? AND owner_id = ?", symbol, id)) > 1:
                share_sum = db.execute("SELECT SUM(share_count) FROM stocks WHERE name = ? AND owner_id = ?", symbol, id)[0]['SUM(share_count)']
                db.execute("DELETE FROM stocks WHERE name = ? AND owner_id = ?", symbol, id)
                db.execute("INSERT INTO stocks (name, share_count, price, owner_id) VALUES (?,?,?,?)", symbol, share_sum, price, id)

            db.execute("DELETE FROM stocks WHERE share_count = 0 AND owner_id = ?", id)
            db.execute("INSERT INTO history (type, name, shares, price, id, time) VALUES (?,?,?,?,?,?)", "Bought", name, shares, price, id, datetime.now())
            return redirect("/")
            # return render_template("buy.html", symbol=symbol, shares=shares, price=price, total=total, cash=cash)

        
@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    if request.method == "GET":
        return render_template("sell.html")
    else:
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
        elif shares == 0:
            return render_template("sell.html", error="no_shares", er=True)
        else:
            db.execute("UPDATE stocks SET share_count = share_count - ? WHERE owner_id = ? AND name = ?", shares, id, symbol)
            db.execute("DELETE FROM stocks WHERE share_count = 0 AND owner_id = ?", id)
            db.execute("UPDATE users SET cash = cash + ? WHERE id = ?", total, id)
            db.execute("INSERT INTO history (type, name, shares, price, id, time) VALUES (?,?,?,?,?,?)", "Sold", name, shares, price, id, datetime.now())
            # return render_template("sell.html", symbol=symbol, shares=shares, price=price, total=total, cash=cash)
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
    return render_template("history.html", history=history, len=n)


@app.route("/groups", methods=["GET","POST"])
@login_required
def groups():
    id = session["user_id"]
    if db.execute("SELECT ext_user_id FROM group_links WHERE ext_user_id = ?", id):
        if request.method == "GET":
            group_id = db.execute("SELECT ext_group_id FROM group_links WHERE ext_user_id = ?", id)[0]['ext_group_id']
            group_name = db.execute("SELECT group_name FROM groups WHERE group_id = ?", group_id)[0]["group_name"]
            group_user_ids = db.execute("SELECT ext_user_id FROM group_links WHERE ext_group_id = ?", group_id)
            user_len = len(group_user_ids)
            for i in range(user_len):
                group_user_ids[i] = group_user_ids[0]['ext_user_id']

            group_users = []
            i = 0
            for user_id in group_user_ids:
                username = db.execute("SELECT username FROM users WHERE id = ?", user_id)[0]['username']
                cash = db.execute("SELECT cash FROM users WHERE id = ?", user_id)[0]['cash']
                portfolio_value = cash

                for asset in db.execute("SELECT name, SUM(share_count) FROM stocks WHERE owner_id = ? GROUP BY name", user_id):
                    stock = lookup(asset['name'])
                    price = stock['price']
                    shares = asset['SUM(share_count)']
                    stock_total = price * shares
                    portfolio_value += stock_total

                group_users.append({
                    'id': user_id,
                    'name': username,
                    'portfolio_value': round(portfolio_value, 2)
                })
                i += 1
                
            sorted(group_users, key=lambda x: x['portfolio_value'], reverse=True)
            print(group_users)

            teacher_status = db.execute('SELECT is_teacher FROM group_links WHERE ext_user_id = ?', id)[0]['is_teacher']
            if teacher_status == 1:
                is_teacher = True
            else:
                is_teacher = False

            group_cash_sum = 0
            for n in range(i):
                group_cash_sum += group_users[n]['portfolio_value']
            group_cash_average = round((group_cash_sum / i), 2)

            now = datetime.now().replace(microsecond=0)

            # subgroups
            subgroups = db.execute('SELECT subgroup_id FROM subgroups WHERE main_group = ?', group_id)

            for i in range(len(subgroups)):
                # make array only contain ids
                subgroups[i] = subgroups[i]['subgroup_id']

            for subgroup in subgroups:
                subgroup_name = db.execute("SELECT subgroup_name FROM subgroups WHERE subgroup_id = ?", subgroup)[0]['subgroup_name']
                subgroup_users = db.execute('SELECT ext_user_id FROM subgroup_links WHERE ext_subgroup_id = ?', subgroup)

                for j in range(len(subgroup_users)):
                    subgroup_users[j] = subgroup_users[j]['ext_user_id']

                for sub_id in subgroup_users:
                    sub_username = db.execute('SELECT username FROM users WHERE id = ?', sub_id)[0]['username']
                    sub_cash = round((db.execute('SELECT cash FROM users WHERE id = ?', sub_id)[0]['cash']), 2)

                    sub_users = {}
                    n = 0
                    sub_portfolio_value = sub_cash

                    # get portfolio value for each user
                    for asset in db.execute('SELECT name, SUM(share_count) FROM stocks WHERE owner_id = ', sub_id):
                        stock = lookup(asset)
                        price = stock['price']
                        shares = asset[0]['SUM(share_count)']
                        stock_total = price * shares
                        sub_portfolio_value += stock_total

                    # add user info
                    sub_users[n] = {
                        'name': sub_username,
                        'portfolio_value': sub_portfolio_value
                    }
                    n += 1

                    # calculate average
                    sorted_sub_users = []
                    for p in range(n):
                        sorted_sub_users.append(sub_users[p]['portfolio_value'])

                    sorted_group_users.sort(reverse=True)
                    sub_cash_sum = 0
                    for cash in sorted_group_users:
                        sub_cash_sum += cash
                    sub_cash_average = round((sub_cash_sum / n), 2)

                    # add to array of subgroups
                    sub_groups = {}
                    m = 0
                    sub_groups[m] = {
                        'name': subgroup_name,
                        'description': 'null',
                        'users': sub_users,
                        'cash_average': sub_cash_average,
                    }

            return render_template("dashboard.html", group_name=group_name, group_users=group_users, len=i, is_teacher=is_teacher, group_cash_average=group_cash_average, usd=usd, datetime=now, subgroups=subgroups, len_=len)
    else:
        if request.method == "GET":
            return render_template("join_groups.html")
        else:
            group_name = request.form.get("group_name")
            group_id = db.execute("SELECT group_id FROM groups WHERE group_name LIKE ?", group_name)[0]["group_id"]
            group_key = request.form.get("group_key")

            arnold_key = db.execute("SELECT group_key FROM groups WHERE group_id = ?", group_id)[0]["group_key"]
            if pass_check(arnold_key, group_key):
                if request.form.get("teacher_key"):
                    teacher_key = request.form.get("teacher_key")
                    arnold_key_2 = db.execute("SELECT teacher_key FROM groups WHERE group_name LIKE ? LIMIT 1", group_name)[0]["teacher_key"]
                    if pass_check(arnold_key_2, teacher_key):
                        db.execute("INSERT INTO group_links (ext_group_id, ext_user_id, is_teacher) VALUES (?,?,?)", group_id, id, 1)
                        return redirect("/groups")
                    else:
                        return render_template("join_groups.html", error="teacher_key", er=True)
                else:
                    db.execute("INSERT INTO group_links (ext_group_id, ext_user_id, is_teacher) VALUES (?,?,?)", group_id, id, 0)
                    return redirect("/groups")
            else:
                return render_template("join_groups.html", error="group_key", er=True)

                    

    
@app.route("/logout")
@login_required
def logout():
    # fogert user id
    session.clear()

    # redirect user to homepage
    return render_template("homepage.html", success="TRUE2")