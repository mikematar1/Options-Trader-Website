from flask import Flask,render_template,request,redirect
from flask_socketio import SocketIO,send
from flask_sqlalchemy import SQLAlchemy
import yfinance as yf
import threading,time
import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI']="sqlite:///user.db"
app.config['SECRRET_KEY']="secretkey"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
socketio = SocketIO(app)
signedin=False
signedinuser=[]
balance=""
clients=""
openstock=""
lasty=0
lastx=0
keeptrack=[]
@socketio.on('connect')
def handleclient():
    print("connection")
    global clients
    clients=request.sid



def dostuff():
    global lastx,lasty
    while True:
        y,x = openstock.getprices("1d","1d")
        
        if y[-1]!=lasty:
            keeptrack.append((x[-1],y[-1]))
            lastx,lasty=(x[-1],y[-1])
        time.sleep(10)

@socketio.on("message")
def handlemsg(msg):
    # threading.Thread(target=dostuff).start()
    y,x = openstock.getprices("1d","1m")
    
    global lasty
    global lastx
    if y[-1]!=lasty:
        t = trade.query.filter_by(userid=signedinuser[0].id,stockid=openstock.id).all()
        t = list(map(lambda h: (h.keeptrack()[1]/100)*h.amount,t))
        socketio.send([y[-1],datetime.datetime.now().strftime("%H:%M"),t])
        lasty=y[-1]
        lastx=x[-1]
    elif msg=="hello mate":
        t = trade.query.filter_by(userid=signedinuser[0].id,stockid=openstock.id).all()
        t = list(map(lambda h:(h.keeptrack()[1]/100)*h.amount,t))
        socketio.send([y[-1],datetime.datetime.now().strftime("%H:%M"),t])
    else:
        socketio.send(lasty)

    
    


class stock(db.Model):
    id = db.Column("id",db.Integer,primary_key=True)
    name=db.Column(db.String(100))

    def __init__(self,name):
        self.name=name
    
    def getprices(self,p="10d",i="1d"):
        import yfinance as yf      
        data = yf.Ticker(self.name)
        hist = data.history(period=p,interval=i)
        closeprices = list(hist['Close'].values)
        openprices=list(hist['Open'].values)
        dates = list(map(lambda y:str(y)[:10],list(hist['Close'].keys().values)))
        
        
        prices=[]
        x=0
        for i in range(len(closeprices)):
            prices+=[openprices[i]]
            prices+=[closeprices[i]]
            if i==len(closeprices)-1:
                dates.insert(i+1+x,datetime.datetime.now().strftime("%H:%M"))
            else:
                dates.insert(i+1+x,"12:00")
            x+=1
       
        return prices,dates
    

    

class user(db.Model):
    
    id = db.Column("id",db.Integer, primary_key=True)
    username=db.Column(db.String(80))
    password=db.Column(db.String(90))
    balance = db.Column(db.Integer)
    def __init__(self,username,password,balance):
        self.username=username
        self.password=password
        self.balance=balance
    def getbalance(self):
        return self.balance

class trade(db.Model):
    id=db.Column("id",db.Integer,primary_key=True)
    tradetype=db.Column(db.String(40))
    atprice=db.Column(db.Integer)
    stockid = db.Column(db.Integer)
    userid=db.Column(db.Integer)
    amount=db.Column(db.Integer)
    def __init__(self,tradetype,atprice,stockid,userid,amount):
        self.tradetype=tradetype
        self.atprice=atprice
        self.stockid=stockid
        self.userid = userid
        self.amount=amount
    def keeptrack(self):
        currentprice = stock.query.get(self.stockid).getprices("1d","1m")[0][-1]
        if self.tradetype=="sell":
            change = self.atprice - currentprice
            changepercentage = change/self.atprice
            return change,changepercentage
        else:
            change=currentprice - self.atprice
            changepercentage = change*100/self.atprice
            return change,changepercentage
    def withdraw(self):
        c1,c2 = self.keeptrack()
        amount = self.atprice +(c2/100)*self.atprice
        user.query.get(signedinuser[0].id).balance+=amount
        db.session.commit()
        a=user.query.get(signedinuser[0].id)
        signedinuser.clear()
        signedinuser.append(a)





    






@app.route("/")
def main():
    global balance
    if signedin:
        balance=str(signedinuser[0].balance)
    # data = yf.Ticker("AAPL")
    hist = yf.download("AAPL",period="10d",interval="1d")
    y1=list(hist['Close'].values)
    x1 = list(hist['Close'].keys().values)
    x1 = list(map(lambda y: str(y)[:10],x1))

    # data = yf.Ticker("TSLA")
    hist = yf.download("TSLA",period="10d",interval="1d")
    y2=list(hist['Close'].values)
    x2 = list(hist['Close'].keys().values)
    x2 = list(map(lambda y: str(y)[:10],x2))

    # data = yf.Ticker("GOOGL")
    hist = yf.download("GOOGL",period="10d",interval="1d")
    y3=list(hist['Close'].values)
    x3 = list(hist['Close'].keys().values)
    x3 = list(map(lambda y: str(y)[:10],x3))

    return render_template("main.html",signedin=signedin,y1=y1,x1=x1,x2=x2,y2=y2,x3=x3,y3=y3,balancex=balance)



@app.route("/signup",methods=['POST','GET'])
def signup():
    return render_template("signup.html")



@app.route("/adduser",methods=['POST','GET'])
def adduser():
    username = request.form['username']
    password1 = request.form['repeatpassword']
    password = request.form['password']
    if password==password1:
        a = user(username=username,password=password,balance=0)
        db.session.add(a)
        db.session.commit()
        global signedin
        
        
        return redirect("/")
    else:
        return redirect("/signup")


@app.route("/signinn")
def signinn():
    return render_template("signin.html")


@app.route("/signin",methods=['POST','GET'])
def signin():
    username = request.form['username']
    password = request.form['password']
    try:
        users = user.query.filter_by(username=username).first()
        if users.password==password:
            global signedin
            signedin=True
            signedinuser.append(users)
            return redirect("/")
        else:
            return redirect("/signinn")
    except:
        return redirect("/signinn")

        
        

@app.route("/stockcurve/<int:id>/<string:p>/<string:i>",methods=['POST','GET'])
def stockc(id,p,i):
    
    global balance
    if signedin:
        balance=str(signedinuser[0].balance)
    stockb = stock.query.get(id)
    y,x =stockb.getprices(p,i)
    global openstock
    global lasty
    global lastx
    lasty=y[-1]
    lastx=x[-1]
    openstock = stockb
    
    

    return render_template('stockcurve.html',x=x,y=y,id=id,stock=stockb,balancex=balance)



@app.route("/signout")
def signout():
    global signedin 
    signedin=False
    signedinuser.clear()
    return redirect("/")

@app.route("/stocklist")
def stocklist():
    global balance
    if signedin:
        balance=str(signedinuser[0].balance)
    if signedin:
        stocks = stock.query.all()
        return render_template("stocklist.html",stocks=stocks,balancex=balance)
    else:
        return redirect("/signup")

@app.route("/admin")
def admin():
    return render_template("admin.html")

@app.route("/adminstockadd",methods=['POST','GET'])
def addstock():
    stockname = request.form['stockname']
    bb = stock(name=stockname)
    db.session.add(bb)
    db.session.commit()
    return redirect("/admin")

@app.route("/buy/<int:id>/<float:buyprice>",methods=['POST','GET'])
def buy(id,buyprice):
    price = int(request.form['buyvalue'])

    t = trade("buy",buyprice,id,signedinuser[0].id,price)
    db.session.add(t)
    user.query.get(signedinuser[0].id).balance-=price
    db.session.commit()
    a=user.query.get(signedinuser[0].id)
    signedinuser.clear()
    signedinuser.append(a)
    return redirect(f"/stockcurve/{id}/50d/1d")

@app.route("/sell/<int:id>/<float:sellprice>",methods=['POST','GET'])
def sell(id,sellprice):
    price = int(request.form['sellvalue'])

    t=trade("sell",sellprice,id,signedinuser[0].id,price)
    db.session.add(t)
    user.query.get(signedinuser[0].id).balance-=price
    db.session.commit()
    a=user.query.get(signedinuser[0].id)
    signedinuser.clear()
    signedinuser.append(a)
    return redirect(f"/stockcurve/{id}/50d/1d")

@app.route("/deposit")
def deposit():
    return render_template("deposit.html")

@app.route("/makedeposit/",methods=['POST','GET'])
def makedeposit():
    amount = int(request.form['payment'])
    user.query.get(signedinuser[0].id).balance+=amount
    db.session.commit()
    a=user.query.get(signedinuser[0].id)
    signedinuser.clear()
    signedinuser.append(a)

    return redirect("/")

@app.route("/closetrade/<int:id>",methods=['POST','GET'])
def removetrade(id):
    a=trade.query.filter_by(userid = signedinuser[0].id,stockid=openstock.id).all()[id]
    a.withdraw()
    db.session.delete(a)
    db.session.commit()
    return redirect(f"/stockcurve/{openstock.id}/50d/1d")

if __name__=="__main__":
    db.create_all()
    
    socketio.run(app)
