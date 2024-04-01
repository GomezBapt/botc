from binance.client import Client
from binance.enums import *
from time import time, sleep

# clés de demo pour l'api
demo = [("KIOi6daduoM37dj135wOHtetbgZkJbl4KceYCNs2QE7r6XZuCwfDR41YtIFloFev", "l740EzoI5ZM2ODhp9pn1JUAUQPrkKvuls8wZbHkEMY4fCnlPDmHxQrUkr6m1WMDW"),
        ("7AtM3eMGbT4JAv9mpToQrQoz4ijlGEPZoy5lryBaCLEne0uS3yGMaDkxC3qAeAqs", "ZD6nL9VZHNgkJYRHvlM8aBDhaDpm1kDGc9ZtKIXM253d2zkbtbzO8uN3cXwZG5Jw"),
        ("BFPxbphupLOLXZkHncovKq1UQlPZNQ1po6rPyu60m0ZVjrhQhJnq7sbe30ASloyz", "KFlEdUmCUVI4I9EkQYuGybh19j79QanbEwbTtpwslfibohAgWBfIYtjGpGDcn0ce")
        ]

def get_balance(client, ticker):
  return client.get_asset_balance(asset=ticker)["free"]

def show_balance(client, ticker):
  print(f"You have {get_balance(client,ticker)} {ticker}")

def other_side(side):
  if side == SIDE_BUY:
    return SIDE_SELL
  return SIDE_BUY

def order(type, ticker, amount, client : Client, debug):
  side = 0
  if type == "buy":
    side = SIDE_BUY
  else:
    side = SIDE_SELL
  price_predict = float(client.get_recent_trades(symbol=ticker, limit=1)[0]["price"])
  qty = 0
  size = len(client.get_symbol_info(ticker)["filters"][1]["stepSize"].split("1")[0])-1
  if ticker[-4:] == "USDT" or ticker[-4:] == "USDC" or ticker[-4:] == "TUSD":
    qty = round(amount/price_predict,size)
  else:
    side = other_side(side)
    qty = amount
  qty = f"{qty:.5f}"
  try:
    order = client.create_order(symbol=ticker, side=side, type=ORDER_TYPE_MARKET, quantity=str(qty))
    fill = order["status"]
    if fill == "FILLED":
      if debug:
        price = round(float(order["fills"][0]["price"]),8)
        if ticker[-4:] == "USDT" or ticker[-4:] == "USDC":
          if side == SIDE_BUY:
            print(f"Bought {qty} {ticker[:-4]} at {price} for {float(qty)*price} USDT")
          else:
            print(f"Sold {qty} {ticker[:-4]} at {price} for {float(qty)*price} USDT")
          return qty
        else:
          if side == SIDE_SELL:
            print(f"Bought {float(qty)*price} {ticker[4:]} at {price} for {qty} USDT")
          else:
            print(f"Sold {float(qty)*price} {ticker[4:]} at {price} for {qty} USDT")
          return float(qty)*price
    else:
      print("Order not filled")
  except Exception as e:
    print(e)

def sell_all(client, ticker, amount, debug):
  order = client.create_order(symbol=ticker, side=SIDE_SELL, type=ORDER_TYPE_MARKET, quantity=amount)
  if debug:
    if order["status"] == "FILLED":
      print(f"Sold {amount}")
      price = round(float(order["fills"][0]["price"]),8)
      return price
    else:
      print("Order sell failed")
      return -1


def recherche(client, max_var, time):
  found = list()

  # filtres (stablecoins ou monnaies mondiales)
  filters = ["USDC", "DAI", "PAXG", "TUSD", "USDP", "AEUR", "EUR", "BRL", "FDUSD", "PLN", "ARS", "TRY", "ZAR", "IDRT", "UAH"]

  def verif_filter(ticker):
    for filter in filters:
      if filter in ticker:
        return False
    return True

  # on recupère toutes les paires
  tickers = client.get_all_tickers()

  print(f"Nombre de tickers récupérés : {len(tickers)}")

  for all in tickers:
    ticker = all["symbol"]
    # on veut que les paires avec USDT
    if "USDT" in ticker and verif_filter(ticker):
      # on récu^père les prix journaliers
      klines = client.get_historical_klines(ticker, Client.KLINE_INTERVAL_1DAY, f"{time} day ago UTC")
      verif = True
      for kline in klines:
        # variation journalière
        if 100*abs(float(kline[1]) - float(kline[4]))/abs(float(kline[1])) > max_var:
          verif = False
      if verif:
        print(f"{ticker} did not changed for more than {max_var}% in a day for {len(klines)} days")
        found.append(ticker)
  return found

def sma(client, ticker, interval, size):
  data = client.get_klines(symbol=ticker, interval=interval)
  moy = 0
  i = 1
  while i < size+1:
    moy += float(data[-i][4])
    i += 1
  moy /= size
  return moy

def update_sma(client, ticker, interval, size, actual):
  new = sma(client, ticker, interval, size)
  old = actual
  pente = new-old
  return old, new, pente

def strategy_sma_x_y(low, high, interval, pourcent, asset, target, update, debug, auth):
  print(f"Strategy : {low} -- {high} -- {interval} -- {pourcent}% -- {target}{asset}")

  key = auth[0]
  secret = auth[1]

  client = Client(key,secret)

  # url de demo
  client.API_URL = 'https://testnet.binance.vision/api'

  btc = client.get_asset_balance(asset=target)["free"]

  ticker = f"{target}{asset}"

  if float(btc) > 0:
    sell_all(client, ticker, btc, False)

  btc = client.get_asset_balance(asset=target)["free"]
  usdt = client.get_asset_balance(asset=asset)["free"]
  print(f"Started with {usdt} {asset}")
  f = open("data.txt", "a")
  f.write(f"{usdt}\n")
  f.close()

  lt = 450
  pourcent = pourcent/100
  new_low = sma(client, ticker, interval, low)
  new_high = sma(client, ticker, interval, high)
  stable = sma(client, ticker, interval, lt)
  pente = 1
  changed = False

  while True:
    changed = False
    start = time()
    old_low, new_low, trash = update_sma(client, ticker, interval, low, new_low)
    old_high, new_high, pente = update_sma(client, ticker, interval, high, new_high)
    trash, stable, pstable = update_sma(client, ticker, interval, lt, stable)

    if (new_low > new_high and old_low < old_high and pente > 0 and pstable > 0):
      usdt = client.get_asset_balance(asset=asset)["free"]
      order("buy", ticker, float(usdt)*pourcent, client, False)
      changed = True

    if (new_low < new_high and old_low > old_high and float(btc) > 0) or pente < 0:
      btc = client.get_asset_balance(asset=target)["free"]
      if float(btc) > 0:
        sell_all(client, ticker, btc, False)
        usdt = client.get_asset_balance(asset=asset)["free"]
        f = open("data.txt", "a")
        f.write(f"{usdt}\n")
        f.close()
        changed = True

    if debug:
      print(f"Delta : {new_high-new_low}")
    if changed:
      if debug:
        print("Crossed")

      btc = client.get_asset_balance(asset=target)["free"]
      usdt = client.get_asset_balance(asset=asset)["free"]
      print(f"I have {btc} {target} and {usdt} {asset}")

    elapsed = time() - start

    if abs(elapsed) < update:
      slept = update-abs(elapsed)
      sleep(slept)



#max_var = float(input("Variation maximale en un jour en pourcent : "))
#time = int(input("Nombres de jours : "))
#recherche(client, max_var, time)
strategy_sma_x_y(25, 100, KLINE_INTERVAL_1MINUTE, 1, "USDT", "BTC", 60, False, demo[1])










"""auth = demo[1]
key = auth[0]
secret = auth[1]

client = Client(key,secret)

client.API_URL = 'https://testnet.binance.vision/api'

usdt = client.get_asset_balance(asset="USDC")["free"]
size = len(client.get_symbol_info('BTCUSDT')["filters"][1]["stepSize"].split("1")[0])-1
print(size)
print(f"I have {usdt} USDC")
ticker = "ETHUSDC"
pourcent = 0.2
order("buy", ticker, float(usdt)*pourcent, client, True)
show_balance(client, "ETH")"""