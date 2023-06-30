from financial_data import SECDataRetriever

print("Please enter email to access SEC api.")
email = input()
print("Please enter ticker.")
ticker = input()

call = SECDataRetriever(email)
income, balance, cashflow = call.financial_statements(ticker)
print(income)
print(balance)
print(cashflow)