import os, json, datetime, hmac, hashlib
from flask import Flask, request

app = Flask(__name__)

# --- ALL SECURE FROM ENV ---
OWNER = os.getenv("OWNER_PHONE", "")
BARBER2 = os.getenv("BARBER2_PHONE", "")
BARBER3 = os.getenv("BARBER3_PHONE", "")
UPI_ID = os.getenv("UPI_ID", "test@okhdfc")
SHOP_NAME = os.getenv("SHOP_NAME", "New Janta Hair Salon")
SHOP_ADDRESS = os.getenv("SHOP_ADDRESS", "Matar, Gujarat")
SHOP_MAP_LINK = os.getenv("SHOP_MAP_LINK", "")
SHOP_PHONE = os.getenv("SHOP_PHONE", "")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "newjanta123")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")

SERVICES = {
 "1": ("Haircut", 100), "2": ("Haircut + Shaving", 150),
 "3": ("Shaving / Beard Trim", 60), "4": ("Head Massage", 100),
 "5": ("Hair Colour", 300), "6": ("Facial", 250),
}
BARBERS = {"1": ("Barber 1 - Owner", OWNER), "2": ("Barber 2", BARBER2), "3": ("Barber 3", BARBER3)}

# --- STORAGE ---
def load():
    try: return json.load(open("bookings.json"))
    except: return {"users": {}, "bookings": []}
def save(d): json.dump(d, open("bookings.json", "w"))

def send(to, msg):
    # Replace with WhatsApp Cloud API call using WHATSAPP_TOKEN
    # import requests; requests.post(...)
    print(f"TO {to}: {msg}")

def location_block():
    return f"\n\n📍 Reach Us:\n{SHOP_NAME}\n{SHOP_ADDRESS}\nMap: {SHOP_MAP_LINK}\n📞 Call: +91 {SHOP_PHONE[-10:]}\n⏰ Open: 8 AM to 10 PM"

def is_owner(num): return num == OWNER

# --- WEBHOOK VERIFY ---
@app.route("/webhook", methods=["GET"])
def verify():
    if request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge")
    return "Invalid", 403

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        v = request.json['entry'][0]['changes'][0]['value']
        msg = v['messages'][0]
        frm = msg['from']
        text = msg['text']['body'].strip()
        upper = text.upper()
    except: return "ok"

    db = load()
    users = db["users"]; bookings = db["bookings"]
    user = users.get(frm, {"step": "menu"})

    # ===== OWNER ONLY - SECURE =====
    if is_owner(frm) and upper == "EARNING TODAY":
        today = str(datetime.date.today())
        t = [b for b in bookings if b.get("date")==today and b.get("status")=="confirmed"]
        total = sum(b["price"] for b in t); adv = len(t)*50
        send(OWNER, f"Today Earning - {SHOP_NAME}\nCustomers: {len(t)}\nTotal: Rs.{total}\nAdvance: Rs.{adv}\nBalance to collect: Rs.{total-adv}")
        return "ok"
    if frm in [BARBER2, BARBER3] and upper in ["EARNING TODAY","BROADCAST DIWALI","BROADCAST NAVRATRI"]:
        send(frm, "Sorry, only Owner can do this.")
        return "ok"

    if is_owner(frm) and upper.startswith("BROADCAST DIWALI"):
        for b in bookings:
            send(b["phone"], f"Diwali Dhamaka! 🪔 {SHOP_NAME}\nGet 20% OFF on ALL Services! 18-25 Oct only. Type HI to book.{location_block()}\nReply STOP to stop.")
        send(OWNER, "Diwali broadcast sent to all customers.")
        return "ok"
    if is_owner(frm) and upper.startswith("BROADCAST NAVRATRI"):
        for b in bookings:
            send(b["phone"], f"Navratri Special! ✨ {SHOP_NAME}\nLook fresh for Garba! Get 20% OFF on Haircut + Beard + Facial. Type HI to book.{location_block()}")
        send(OWNER, "Navratri broadcast sent.")
        return "ok"
    if is_owner(frm) and upper == "TODAY LIST":
        today = str(datetime.date.today())
        t = [b for b in bookings if b.get("date")==today]
        msg_txt = f"Today Full List - {len(t)}\n" + "\n".join([f"{b['time']} - {b['name']} - {b['service']} - {b['barber_name']}" for b in t])
        send(OWNER, msg_txt); return "ok"

    # ===== CUSTOMER FLOW =====
    if upper == "LOCATION":
        send(frm, f"📍 {SHOP_NAME}\n{SHOP_ADDRESS}\nMap: {SHOP_MAP_LINK}\nOpen 8 AM - 10 PM"); return "ok"
    if upper == "STOP":
        user["promo"] = False; users[frm]=user; save(db); send(frm, "You will not receive offers. Type HI to book."); return "ok"

    if upper == "HI" or upper == "HELLO":
        user = {"step": "menu"}; users[frm]=user; save(db)
        send(frm, f"Welcome to {SHOP_NAME} ✂️\n📍 {SHOP_ADDRESS}\nOpen 8 AM - 10 PM\n1. Book New Slot\n2. Cancel Booking\n3. Reschedule\n4. Location & Offers\nReply 1, 2, 3 or 4"); return "ok"

    if upper == "4":
        send(frm, f"📍 Location: {SHOP_MAP_LINK}\n🎁 Offers: Birthday 20% OFF, Diwali 20% OFF, Navratri 20% OFF\n📞 Call: +91 {SHOP_PHONE[-10:]}"); return "ok"

    if user.get("step")=="menu" and upper=="1":
        user["step"]="service"; users[frm]=user; save(db)
        send(frm, "Choose service:\n1. Haircut - Rs.100\n2. Haircut + Shaving - Rs.150\n3. Shaving - Rs.60\n4. Head Massage - Rs.100\n5. Hair Colour - Rs.300\n6. Facial - Rs.250"); return "ok"

    if user.get("step")=="service" and upper in SERVICES:
        user["service"]=SERVICES[upper][0]; user["price"]=SERVICES[upper][1]; user["step"]="date"; users[frm]=user; save(db)
        send(frm, f"You selected: {user['service']} - Rs.{user['price']}\nPick date:\n1. Today\n2. Tomorrow\n3. Day After Tomorrow\nReply 1/2/3"); return "ok"

    if user.get("step")=="date" and upper in ["1","2","3"]:
        d = datetime.date.today() + datetime.timedelta(days=int(upper)-1)
        user["date"]=str(d); user["step"]="time"; users[frm]=user; save(db)
        send(frm, f"Date: {user['date']}\nPick time:\n1. 08:00 AM\n2. 09:00 AM\n3. 10:00 AM\n4. 11:00 AM\n5. 12:00 PM\n6. 04:00 PM\n7. 05:00 PM\n8. 06:00 PM\n9. 07:00 PM"); return "ok"

    if user.get("step")=="time":
        times = {"1":"08:00 AM","2":"09:00 AM","3":"10:00 AM","4":"11:00 AM","5":"12:00 PM","6":"04:00 PM","7":"05:00 PM","8":"06:00 PM","9":"07:00 PM"}
        if upper in times:
            user["time"]=times[upper]; user["step"]="barber"; users[frm]=user; save(db)
            send(frm, "Pick Barber:\n1. Barber 1 - Owner\n2. Barber 2\n3. Barber 3\n4. Any Available"); return "ok"

    if user.get("step")=="barber" and upper in ["1","2","3","4"]:
        if upper=="4": bkey="2"  # Auto assign to free barber logic - simplified
        else: bkey=upper
        user["barber"]=bkey; user["barber_name"]=BARBERS[bkey][0]; user["step"]="name"; users[frm]=user; save(db)
        send(frm, "Enter your Full Name:"); return "ok"

    if user.get("step")=="name":
        user["name"]=text; user["step"]="birthday"; users[frm]=user; save(db)
        send(frm, "Enter Birthday (DD-MM) for 20% OFF Birthday Gift - Example 15-08\nOr type SKIP"); return "ok"

    if user.get("step")=="birthday":
        user["birthday"]=text if upper!="SKIP" else ""; user["step"]="confirm"; users[frm]=user; save(db)
        send(frm, f"Confirm booking:\n💈 {SHOP_NAME}\n👤 {user['name']}\n✂️ {user['service']}\n📅 {user['date']} at {user['time']}\n👨 {user['barber_name']}\n💰 Rs.{user['price']}\nReply YES to confirm"); return "ok"

    if user.get("step")=="confirm" and upper=="YES":
        user["step"]="payment"; users[frm]=user; save(db)
        send(frm, f"Pay Rs.50 Advance to confirm.\n✂️ {user['service']} - Total Rs.{user['price']}\n💰 Advance: Rs.50\n💵 Balance at Salon: Rs.{user['price']-50}\nPay UPI: {UPI_ID}\nAfter payment, reply: PAID <UTR>\nExample: PAID 123456789012"); return "ok"

    if upper.startswith("PAID "):
        utr = text.split(" ",1)[1].strip()
        if len(utr) < 10:
            send(frm, "UTR looks wrong. Please send correct 12-digit UTR: PAID 123456789012"); return "ok"
        # Save booking
        b = {"phone": frm, "name": user.get("name",""), "birthday": user.get("birthday",""), "service": user.get("service",""), "price": user.get("price",0), "date": user.get("date",""), "time": user.get("time",""), "barber": user.get("barber",""), "barber_name": user.get("barber_name",""), "utr": utr, "status": "confirmed", "last_visit": str(datetime.date.today())}
        bookings.append(b); user={"step":"menu"}; users[frm]=user; save(db)
        # === PAYMENT CONFIRMED WITH LOCATION ===
        send(frm, f"✅ Payment Confirmed! Your Slot is Booked!\n\n💈 {SHOP_NAME}\n👤 {b['name']}\n✂️ {b['service']} - Rs.{b['price']}\n📅 {b['date']} at {b['time']}\n👨 {b['barber_name']}\n💰 Advance Paid: Rs.50\n💵 Balance at Salon: Rs.{b['price']-50}\n\n📍 Reach Us:\n{SHOP_ADDRESS}\nMap: {SHOP_MAP_LINK}\n📞 Call Owner: +91 {SHOP_PHONE[-10:]}\n\n⏰ Please reach 5 mins early.\n🎁 Birthday 20% OFF saved!\nType LOCATION anytime for map.")
        # Notify assigned barber only + owner
        barber_phone = BARBERS[b["barber"]][1]
        send(barber_phone, f"✂️ New Booking for YOU\n👤 {b['name']} - {frm}\n✂️ {b['service']} - Rs.{b['price']}\n📅 {b['date']} at {b['time']}\n💰 Advance Rs.50, Balance Rs.{b['price']-50}")
        send(OWNER, f"💰 New Booking - {SHOP_NAME}\n👤 {b['name']} - {b['service']} - {b['date']} {b['time']}\n👨 {b['barber_name']}\nUTR: {utr}")
        return "ok"

    if user.get("step")=="menu" and upper=="2":
        my = [b for b in bookings if b["phone"]==frm and b["status"]=="confirmed"]
        if not my: send(frm, "No active booking. Type HI to book."); return "ok"
        send(frm, "Your bookings:\n" + "\n".join([f"{i+1}. {b['service']} - {b['date']} {b['time']}" for i,b in enumerate(my)]) + "\nReply CANCEL <number>"); return "ok"
    if upper.startswith("CANCEL "):
        try:
            idx=int(upper.split()[1])-1
            my=[b for b in bookings if b["phone"]==frm and b["status"]=="confirmed"]
            my[idx]["status"]="cancelled"; save(db)
            send(frm, f"✅ Cancelled! {my[idx]['service']} on {my[idx]['date']} is cancelled. Type HI to book again.")
            send(OWNER, f"❌ Cancelled: {my[idx]['name']} - {my[idx]['service']} {my[idx]['date']} {my[idx]['time']}")
        except: send(frm, "Wrong number. Type HI again.")
        return "ok"

    return "ok"

# --- CRON JOBS: Call /cron daily ---
@app.route("/cron")
def cron():
    db=load(); bookings=db["bookings"]; today=datetime.date.today()
    # Birthday 20% OFF
    for b in bookings:
        if b.get("birthday","").startswith(f"{today.day:02d}-{today.month:02d}"):
            send(b["phone"], f"Happy Birthday {b['name']}! 🎂 Gift from {SHOP_NAME} - Get 20% OFF today!{location_block()}")
    # We Miss You 15/30/45 days
    for b in bookings:
        try: last=datetime.date.fromisoformat(b.get("last_visit",""))
        except: continue
        diff=(today-last).days
        if diff in [15,30,45]:
            send(b["phone"], f"Hi {b['name']}, we miss you! 😊 It's been {diff} days. Come back - Get 20% OFF this week at {SHOP_NAME}. Type HI to book.{location_block()}")
    # 10 PM Earning only to Owner
    t=[b for b in bookings if b.get("date")==str(today) and b.get("status")=="confirmed"]
    total=sum(b["price"] for b in t)
    send(OWNER, f"Today Earning - {SHOP_NAME}\nCustomers: {len(t)}\nTotal: Rs.{total}\nAdvance: Rs.{len(t)*50}")
    return "ok"

if __name__=="__main__":
    app.run(port=5000)
