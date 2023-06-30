import requests
import pandas as pd


class SECDataRetriever:
    """
    This class connects to the SEC api where financial data from company filings can be retrieved.
    API documentation found at https://www.sec.gov/edgar/sec-api-documentation.
    Use https://xbrlsite.azurewebsites.net/2019/Prototype/references/us-gaap/ to find relevant tags.
    All USD values and shares recalculated here per million.
    """
    def __init__(self, email):
        self.header = {'User-Agent': email}  # email required to use sec api
        self.company_tickers = requests.get("https://www.sec.gov/files/company_tickers.json", headers=self.header)
        self.tickers_cik = None
        self.ticker = None
        self.cik = None
        self.ticker_mapping()

    def ticker_mapping(self):
        """Use the company ticker to cik mapping provided by the SEC api and create a dataframe with it."""
        self.tickers_cik = pd.json_normalize(pd.json_normalize(self.company_tickers.json(), max_level=0).values[0])
        self.tickers_cik["cik_str"] = self.tickers_cik["cik_str"].astype(str).str.zfill(10)
        self.tickers_cik.set_index("ticker", inplace=True)

    def set_ticker(self, ticker):
        """Set the ticker attribute, and it's matching cik value using the mapping."""
        self.ticker = ticker
        self.cik = self.tickers_cik.loc[self.tickers_cik.index == self.ticker, "cik_str"].item()

    def tag_data(self, tag, name, units):
        """Request the data matching the tag from the SEC api, and transform this json into a dataframe.
        Keep only the latest filed annual forms (10K, 10K/A, 8K)."""
        response = requests.get("https://data.sec.gov/api/xbrl/companyconcept/CIK"+self.cik+"/us-gaap/"+tag+".json",
                                headers=self.header)
        data = pd.json_normalize(response.json()["units"][units])
        # choose the forms to get data from (10k = annual, 10q = quarterly)
        data = data.loc[data.form.isin(["10-K", '10-K/A', '8-K'])]
        data = data.loc[(data.frame.str.len() == 6) | (data.frame.str.len() == 9)]  # Frame either CY#### or CY####Q#I
        data = data.rename(columns={'val': name, 'end': 'Period End'})
        if units != "USD/shares":
            data[name] = data[name]/(10**6)   # want data in USD/million for easier analysis
        return data

    def merge_records(self, tags):
        """Merge the different dataframes retrieved from the SEC api on the period end column."""
        records = pd.DataFrame({"Period End": []})
        columns = ["Period End"]
        # loop through each tag to get the relevant data
        for tag, info in tags.items():
            # use try statement to avoid errors in case the data does not exist
            try:
                column_name = info[0]
                units = info[1]
                # get each record
                data = self.tag_data(tag, column_name, units)
                columns.append(column_name)
                # join on whichever has more data
                if len(records) > len(data):
                    join = "left"
                else:
                    join = "right"
                # want to merge on period end and keep only the relevant columns
                records = records.merge(data, left_on='Period End', right_on='Period End', how=join)[columns]
            except:
                print(tag+" Failed!")
        return records

    def format_date(self, df):
        """Take the year as a slice from the period end column and set it as the index of the dataframe."""
        df = df.set_index(df["Period End"].str.slice(0, 4))
        df.index.names = ['Year']
        df["Period End"] = df["Period End"].str.slice(5)
        return df

    def balance_sheet_calculator(self):
        """Retrieve balance sheet related data through relevant tags and calculate additional statistics."""
        # balance sheet tags
        tags = {"CashAndCashEquivalentsAtCarryingValue": ['Cash', "USD"],
                "InventoryNet": ['Inventory', "USD"],
                "AssetsCurrent": ['Current Assets', "USD"],
                "AssetsNoncurrent": ['Non-Current Assets', "USD"],
                "DebtCurrent": ['Current Debt', "USD"],
                "AccountsPayableCurrent": ['Accounts Payable', "USD"],
                "DeferredRevenueCurrent": ['Deferred Revenue', "USD"],
                "LiabilitiesCurrent": ['Current Liabilities', "USD"],
                "LongTermDebt": ['Long-term Debt', "USD"],
                "LiabilitiesNoncurrent": ['Non Current Liabilities', "USD"],
                "Liabilities": ['Liabilities', "USD"],
                "IntangibleAssetsNetExcludingGoodwill": ['Intangible Assets', "USD"],
                "Goodwill": ['Goodwill', "USD"],
                }
        # get data and merge it together into a single dataframe
        balance = self.merge_records(tags)
        # need to do additional important balance sheet calculations
        # use 'all' to check if the columns exist first to avoid errors
        if all(x in balance.columns for x in ['Liabilities', 'Current Liabilities']):
            balance['Non Current Liabilities'] = balance['Liabilities'] - balance['Current Liabilities']
        if all(x in balance.columns for x in ['Current Assets', 'Non-Current Assets']):
            balance['Assets'] = balance["Current Assets"] + balance["Non-Current Assets"]
        if all(x in balance.columns for x in ['Assets', 'Liabilities']):
            balance['Stockholders Equity(BV)'] = balance['Assets'] - balance['Liabilities']
        if all(x in balance.columns for x in ['Assets', 'Intangible Assets', 'Goodwill']):
            balance['Tangible BV'] = balance['Assets'] - balance["Intangible Assets"] - balance["Goodwill"]
        return balance

    def income_statement_calculator(self):
        """Retrieve income statement related data through relevant tags and calculate additional statistics."""
        # income statement tags
        tags = {"Revenues": ['Revenue', "USD"],
                "CostOfGoodsAndServicesSold": ['COGS', "USD"],
                "GrossProfit": ['Gross Profit', "USD"],
                "ResearchAndDevelopmentExpense": ['R&D', "USD"],
                "SellingGeneralAndAdministrativeExpense": ['SGA', "USD"],
                "DepreciationDepletionAndAmortization": ['D&A', "USD"],
                "InterestExpense": ['Interest Expense', "USD"],
                "DirectTaxesAndLicensesCosts": ['Tax', "USD"],
                "EarningsPerShareBasic": ['Basic EPS', "USD/shares"],
                "EarningsPerShareDiluted": ['Diluted EPS', "USD/shares"],
                "NetIncomeLoss": ['Net Income', "USD"]}
        # get data and merge it together into a single dataframe
        income = self.merge_records(tags)
        # calculate revenue (+3-year average) incase it does not exist above, earnings, and margins
        # use 'all' to check if the columns exist first to avoid errors
        if all(x in income.columns for x in ['Gross Profit', 'COGS']):
            income['Revenue'] = income['Gross Profit'] + income['COGS']
        if all(x in income.columns for x in ['Revenue']):
            income['Revenue Avg3'] = income['Revenue'].rolling(3).apply(lambda x: x.mean())
        if all(x in income.columns for x in ['Gross Profit', 'Revenue']):
            income['Gross Margin(%)'] = ((income['Gross Profit'] / income['Revenue']) * 100).round(1)
        if all(x in income.columns for x in ['R&D', 'SGA']):
            income['Operating expense'] = income['R&D'] + income['SGA']
        if all(x in income.columns for x in ['Gross Profit', 'Operating expense']):
            income['EBIT'] = income['Gross Profit'] - income['Operating expense']
        if all(x in income.columns for x in ['EBIT', 'D&A']):
            income['EBITDA'] = income['EBIT'] + income['D&A']
        if all(x in income.columns for x in ['R&D', 'Revenue']):
            income['R&D Margin(%)'] = ((income['R&D'] / income['Revenue']) * 100).round(1)
        if all(x in income.columns for x in ['SGA', 'Revenue']):
            income['SGA Margin(%)'] = ((income['SGA'] / income['Revenue']) * 100).round(1)
        if all(x in income.columns for x in ['EBIT', 'Revenue']):
            income['EBIT Margin(%)'] = ((income['EBIT'] / income['Revenue']) * 100).round(1)
        if all(x in income.columns for x in ['EBITDA', 'Revenue']):
            income['EBITDA Margin(%)'] = ((income['EBITDA'] / income['Revenue']) * 100).round(1)
        if all(x in income.columns for x in ['Net Income', 'Revenue']):
            income['Net Income Margin(%)'] = ((income['Net Income'] / income['Revenue']) * 100).round(1)
        return income

    def cashflow_calculator(self):
        """Retrieve cashflow related data through relevant tags and calculate additional statistics."""
        # cashflow tags
        tags = {"NetCashProvidedByUsedInOperatingActivities": ['CFO', "USD"],
                "NetCashProvidedByUsedInInvestingActivities": ['CFI', "USD"],
                "NetCashProvidedByUsedInFinancingActivities": ['CFF', "USD"],
                "PaymentsOfDividends": ['Dividends', "USD"],
                "RepaymentsOfDebt": ["Debt Repayment", "USD"],
                "PaymentsForRepurchaseOfCommonStock": ["Common Stock Repurchased", "USD"],
                "PaymentsToAcquirePropertyPlantAndEquipment": ['CapEx', "USD"],
                }
        # get data and merge it together into a single dataframe
        cashflow = self.merge_records(tags)
        # calculate net cash flow, free cash flow and the 3-year average operating cashflow
        # use 'all' to check if the columns exist first to avoid errors
        if all(x in cashflow.columns for x in ['CFO', 'CFI', 'CFF']):
            cashflow["NCF"] = cashflow["CFO"] + cashflow["CFI"] + cashflow["CFF"]
        if all(x in cashflow.columns for x in ['CFO', 'CapEx']):
            cashflow["FCF"] = cashflow["CFO"] - cashflow["CapEx"]
        if all(x in cashflow.columns for x in ['CFO']):
            cashflow['CFO Avg3'] = cashflow['CFO'].rolling(3).apply(lambda x: x.mean())
        return cashflow

    def other_statistics(self):
        """A function to retrieve other key information."""
        outstanding_shares = self.tag_data("CommonStockSharesOutstanding", 'Outstanding Shares', units="shares")
        columns = ["Period End", "Outstanding Shares"]
        return outstanding_shares[columns]

    def financial_statements(self, ticker):
        """Combine the financial statements."""
        self.set_ticker(ticker)
        # retrieve income statement, balance sheet and cashflow data
        income = self.income_statement_calculator()
        balance = self.balance_sheet_calculator()
        cashflow = self.cashflow_calculator()
        # use try statement to avoid errors in case the data does not exist
        try:
            stats = self.other_statistics()
        except:
            stats = pd.DataFrame({"Period End": []})
        # add the stats(outstanding shares) to each financial statement
        income = income.merge(stats, left_on='Period End', right_on='Period End', how='left')
        balance = balance.merge(stats, left_on='Period End', right_on='Period End', how='left')
        cashflow = cashflow.merge(stats, left_on='Period End', right_on='Period End', how='left')
        # make additional calculations where data from other dataframes is required
        if all(x in balance.columns for x in ['Stockholders Equity(BV)', 'Outstanding Shares']):
            balance['BV/Share'] = (balance['Stockholders Equity(BV)'] / balance['Outstanding Shares']).round(1)
        if all(x in balance.columns for x in ['Intangible BV', 'Outstanding Shares']):
            balance['TBV/Share'] = ((balance['Stockholders Equity(BV)'] - balance['Intangible BV']) \
                                    / balance['Outstanding Shares']).round(1)
        # create a separate dataframe for additional calculations between cashflow and income statements
        df = cashflow.merge(income, left_on='Period End', right_on='Period End', how='left')
        if all(x in df.columns for x in ['CFO', 'Revenue']):
            cashflow['CFO Margin(%)'] = ((df['CFO'] / df['Revenue']) * 100).round(1)
        if all(x in df.columns for x in ['NCF', 'Revenue']):
            cashflow['NCF Margin(%)'] = ((df['NCF'] / df['Revenue']) * 100).round(1)
        if all(x in df.columns for x in ['FCF', 'Revenue']):
            cashflow['FCF Margin(%)'] = ((df['FCF'] / df['Revenue']) * 100).round(1)
        # create additional year column and set as the index
        income = self.format_date(income)
        balance = self.format_date(balance)
        cashflow = self.format_date(cashflow)
        return income, balance, cashflow
