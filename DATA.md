# Data note

The original analysis uses five input files:

| File expected by the project | Contents |
|---|---|
| `MA Deals 11022025.csv` | M&A announcement and transaction characteristics |
| `Stock Data US.xlsx` | Acquirer stock-price histories |
| `Index.xlsx` | S&P 500 market-index history |
| `Industry.xlsx` | Acquirer industry classifications |
| `ESG.xlsx` | Environmental rankings and carbon-emissions intensity |

These inputs were obtained through Bloomberg and S&P resources available to the research team. They are not distributed in this repository.

To reproduce the workflow, place appropriately licensed versions of the files in the working directory used to run `src/analysis.py`. The input schemas and column names must match those referenced in the script.

The public repository does not grant any right to obtain, use or redistribute third-party data.
