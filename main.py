from financial_data import SECDataRetriever
from excel_dashboard import stock_dashboard_generator


def main():
    """
    Main function takes in email and ticker as input and saves the respective spreadsheet in the
    dashboard folder.
    """
    print("Please enter email to access SEC api.")
    email = input()
    print("Please enter ticker.")
    ticker = input()
    call = SECDataRetriever(email)
    income, balance, cashflow = call.financial_statements(ticker)
    stock_dashboard_generator(ticker, income, balance, cashflow)


if __name__ == '__main__':
    main()
