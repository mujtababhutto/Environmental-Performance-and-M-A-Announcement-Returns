# Environmental Performance and M&A Announcement Returns

Do environmental characteristics help explain how investors react when a company announces an acquisition?

This project studies US large-cap M&A announcements between January 2019 and February 2025. It relates the acquiring company’s short-term abnormal return to its environmental ranking, carbon-emissions intensity and deal size, while also considering differences across years and industries.

The research was completed at Frankfurt School of Finance & Management in March 2025. This repository presents the analytical workflow and a public summary of the results; the full paper is not published here.

## Research question

The analysis asks whether acquirers with stronger environmental characteristics experience different stock-market reactions around deal announcements.

Two measures are used to represent environmental performance:

- S&P environmental rank
- carbon emissions relative to sales

The study also classifies acquirers relative to peers in their industry and examines whether the relationship changes across sectors or after the SEC’s March 2022 climate-disclosure proposal.

## Approach

The paper combines M&A transaction data with acquirer stock prices, S&P 500 index data, industry classifications and environmental measures.

The empirical analysis includes:

- event windows around each deal announcement
- cumulative abnormal returns for `[-2,+2]` and `[-10,+10]`
- cross-sectional regressions with deal size and year controls
- industry interaction models
- a difference-in-differences specification around the SEC proposal

## Reported findings

The broad environmental measures have limited explanatory power for acquirer announcement returns in the main regressions. The paper reports differences across industries, although these estimates should be read in the context of the sample composition. The difference-in-differences specification does not identify a significant change for green acquirers after the SEC proposal.

The results point to a useful distinction: environmental performance may matter to investors without necessarily producing a clear, immediate price response around an M&A announcement.

## Repository contents

```text
.
├── docs/
│   ├── index.html
│   └── styles.css
├── src/
│   └── analysis.py
├── DATA.md
├── requirements.txt
└── README.md
```

`src/analysis.py` is the original project script and has been retained as completed. The methodology and reported results have not been revised for this public archive.

## Data availability

The underlying transaction, market and environmental data were obtained through Bloomberg and S&P resources available during the project. Those source files are not included because they are subject to third-party access and redistribution restrictions.

The code therefore documents the analytical workflow but cannot be run end to end without appropriately licensed source data. See [DATA.md](DATA.md) for the expected inputs.

## Authors

- Leonard von Prónay
- Nils Eisaks
- Hendrik Arnemann
- Marco Leibersperger
- Mujtaba Bhutto

Supervisor: Prof. Dr. Thorsten Martin  
Frankfurt School of Finance & Management

## Disclaimer

This repository presents an empirical research project completed in 2025. It is provided for educational and research purposes and does not constitute investment advice.
