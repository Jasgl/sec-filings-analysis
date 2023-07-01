import pandas as pd


def reorder_columns(df, type):
    """A function to reorder the columns for the dashboard."""
    if type == "Income Statement":
        column_order = ['Period End', 'Price', 'Outstanding Shares', 'Market Cap', 'Revenue', 'Revenue Avg3',
                        'COGS', 'Gross Profit', 'R&D', 'SGA', 'Operating expense', 'EBIT', 'D&A', 'EBITDA',
                        'Interest Expense', 'Tax Expense', 'Net Income', 'Gross Margin(%)', 'R&D Margin(%)',
                        'SGA Margin(%)', 'EBIT Margin(%)', 'EBITDA Margin(%)', 'Net Income Margin(%)',
                        'Basic EPS', 'Diluted EPS']
    if type == "Balance Sheet":
        column_order = ['Period End', 'Price', 'Outstanding Shares', 'Market Cap', 'Cash', 'Inventory',
                        'Current Assets', 'Non-Current Assets', 'Assets', 'DebtCurrent', 'AccountsPayableCurrent',
                        'DeferredRevenueCurrent', 'Current Liabilities', 'Long-term Debt',
                        'Non Current Liabilities', 'Liabilities', 'Stockholders Equity(BV)', 'BV/Share',
                        'Tangible BV', 'TBV/Share']
    if type == "Cashflow Statement":
        column_order = ['Period End', 'Price', 'Outstanding Shares', 'Market Cap', 'CFO', 'CFO Avg3', 'CFI', 'CFF',
                        'Dividends', 'Debt Repayment', 'Common Stock Repurchased', 'NCF', 'CapEx', 'FCF',
                        'CFO Margin(%)', 'NCF Margin(%)', 'FCF Margin(%)']
    df = df.reindex(column_order, axis=1).dropna(how='all', axis=1)
    return df.transpose()  # transpose to have year on the horizontal


def stock_dashboard_generator(ticker, income, balance, cashflow):
    # Reorder the columns
    income = reorder_columns(income, "Income Statement")
    balance = reorder_columns(balance, "Balance Sheet")
    cashflow = reorder_columns(cashflow, "Cashflow Statement")
    # separate the statistics into subjective lists of positive, neutral, and negative for the conditional formatting
    positive = ['Revenue', 'Revenue Avg3', 'Gross Profit', 'EBIT', 'EBITDA',
                'Net Income', 'Gross Margin(%)', 'R&D Margin(%)', 'EBIT Margin(%)', 'EBITDA Margin(%)',
                'Net Income Margin(%)', 'Basic EPS', 'Diluted EPS',
                # balance sheet
                'Cash', 'Inventory', 'Current Assets', 'Non-Current Assets', 'Assets', 'DeferredRevenueCurrent',
                'Stockholders Equity(BV)', 'BV/Share', 'Tangible BV',
                # cashflow
                'CFO', 'CFO Avg3', 'CFI', 'Dividends', 'Debt Repayment', 'Common Stock Repurchased',
                'NCF', 'FCF', 'CFO Margin(%)', 'NCF Margin(%)', 'FCF Margin(%)']
    neutral = ['Period End', 'Price', 'Outstanding Shares', 'Market Cap', 'COGS', 'R&D', 'SGA', 'D&A',
               'CapEx']
    negative = ['Operating expense', 'Interest Expense', 'Tax Expense', 'SGA Margin(%)',
                'DebtCurrent', 'AccountsPayableCurrent', 'Current Liabilities', 'Long-term Debt',
                'Non Current Liabilities', 'Liabilities',
                'CFF']
    # Create a Pandas Excel writer using XlsxWriter as the engine.
    writer = pd.ExcelWriter("dashboards//" + ticker + ".xlsx", engine="xlsxwriter")
    # create a dictionary of the financial statement to its dataframe to loop through
    df_to_fs = {"Income Statement": income,
                "Balance Sheet": balance,
                "Cashflow Statement": cashflow}
    # loop through each financial statement to create a separate sheet for each one
    for financial_sheet, df in df_to_fs.items():
        # Convert the dataframe to an XlsxWriter Excel object.
        df.to_excel(writer, sheet_name=financial_sheet)
        # Get the xlsxwriter workbook and worksheet objects.
        workbook = writer.book
        worksheet = writer.sheets[financial_sheet]
        # Get the dimensions of the dataframe.
        (max_row, max_col) = df.shape
        # loop through each row to determine the type of conditional formatting applied to it
        statistics = list(df.index)
        for row in range(max_row):
            if statistics[row] in positive:
                worksheet.conditional_format(row + 1, 1, row + 1, max_col, {"type": "3_color_scale",
                                                                            'min_color': "red",
                                                                            'mid_color': "white",
                                                                            'max_color': "green"})
            if statistics[row] in negative:
                worksheet.conditional_format(row + 1, 1, row + 1, max_col, {"type": "3_color_scale",
                                                                            'min_color': "green",
                                                                            'mid_color': "white",
                                                                            'max_color': "red"})
        column_length = df.index.astype(str).map(len).max()  # find the max length for the strings in the first column
        writer.sheets[financial_sheet].set_column(0, 0, column_length)  # extend the column to this max length
        worksheet.freeze_panes(0, 1)  # Freeze the first row when you are scrolling in Excel
    writer.close()  # Close the Pandas Excel writer and output the Excel file.
