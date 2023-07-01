import yfinance as yf


def price_history(ticker):
    # get historical market data from yahoo finance
    tick = yf.Ticker(ticker)
    hist = tick.history(period='max', interval='1mo')
    hist = hist.reset_index()
    hist = hist.astype({'Date': 'str'})
    hist['Month End'] = hist["Date"].str.slice(0, 7)
    hist['Price'] = hist['Close'].round(2)
    return hist[['Price', 'Month End']]


def format_date(df):
    # Take the year as a slice from the period end column and set it as the index of the dataframe
    df = df.set_index(df["Period End"].str.slice(0, 4))
    df.index.names = ['Year']
    df["Period End"] = df["Period End"].str.slice(5)
    return df


def join_market_data(ticker, income, balance, cashflow):
    history = price_history(ticker)  # get historical data
    # join the data on the year and month
    income['Month End'] = income['Period End'].str.slice(0, 7)
    income = income.merge(history, left_on='Month End', right_on='Month End', how='left')
    balance['Month End'] = balance['Period End'].str.slice(0, 7)
    balance = balance.merge(history, left_on='Month End', right_on='Month End', how='left')
    cashflow['Month End'] = cashflow['Period End'].str.slice(0, 7)
    cashflow = cashflow.merge(history, left_on='Month End', right_on='Month End', how='left')
    # use price data to calculate yearly market cap
    if all(x in income.columns for x in ['Price', 'Outstanding Shares']):
        income['Market Cap'] = income['Price'] * income['Outstanding Shares']
        balance['Market Cap'] = balance['Price'] * balance['Outstanding Shares']
        cashflow['Market Cap'] = cashflow['Price'] * cashflow['Outstanding Shares']
    # organise year and period end
    income = format_date(income)
    balance = format_date(balance)
    cashflow = format_date(cashflow)
    return income, balance, cashflow
