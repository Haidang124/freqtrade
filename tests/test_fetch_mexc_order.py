import ccxt

api_key = "mx0vglaf7Q3iNkxBzA"
api_secret = "0ebc0b45759449beaa40c07b4b4820a2"

exchange = ccxt.mexc({
    'apiKey': api_key,
    'secret': api_secret,
    'enableRateLimit': True,
    'options': {
        'defaultType': 'swap',  # futures
    }
})

symbol = "MIXIE/USDT:USDT"

try:
    open_orders = exchange.fetch_open_orders(symbol)
    print("Open orders:", open_orders)
except Exception as e:
    print("Lỗi khi fetch open orders:", e)

try:
    closed_orders = exchange.fetch_closed_orders(symbol)
    print("Closed orders:", closed_orders)
except Exception as e:
    print("Lỗi khi fetch closed orders:", e) 