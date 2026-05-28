from __future__ import annotations

from pathlib import Path

import pandas as pd

CORE_MARKET_UNIVERSE = [
    # Mega-cap / large-cap technology
    "AAPL",
    "MSFT",
    "NVDA",
    "GOOGL",
    "GOOG",
    "AMZN",
    "META",
    "TSLA",
    "NFLX",
    "ORCL",
    "CRM",
    "ADBE",
    "NOW",
    "INTU",
    "PANW",
    "CRWD",
    "ZS",
    "MDB",
    "WDAY",
    # Semiconductors and AI infrastructure
    "AMD",
    "AVGO",
    "MRVL",
    "ARM",
    "SMCI",
    "MU",
    "TSM",
    "INTC",
    "QCOM",
    "TXN",
    "AMAT",
    "LRCX",
    "ASML",
    "KLAC",
    "MCHP",
    "ON",
    "MPWR",
    "WDC",
    "STX",
    "DELL",
    "HPE",
    "ANET",
    "VRT",
    "ETN",
    # AI / software / high-beta growth
    "PLTR",
    "CRWV",
    "AI",
    "APP",
    "NET",
    "DDOG",
    "SNOW",
    "SHOP",
    "PATH",
    "RBLX",
    "UBER",
    "ABNB",
    "DASH",
    "TWLO",
    "OKTA",
    "HIMS",
    "DUOL",
    "CELH",
    "CAVA",
    "RDDT",
    # Quantum / space / emerging tech
    "IONQ",
    "RGTI",
    "QBTS",
    "QUBT",
    "AMPX",
    "ASTS",
    "RKLB",
    "LUNR",
    "JOBY",
    "ACHR",
    "SOUN",
    "BBAI",
    # Crypto-linked equities and fintech
    "MSTR",
    "COIN",
    "MARA",
    "RIOT",
    "CLSK",
    "IREN",
    "HOOD",
    "SOFI",
    "UPST",
    "AFRM",
    "PYPL",
    "SQ",
    "NU",
    # Retail favorites / high-beta consumer
    "CVNA",
    "GME",
    "AMC",
    "CHWY",
    "DKNG",
    "ROKU",
    "PINS",
    "W",
    "ETSY",
    "LYFT",
    "NIO",
    "RIVN",
    "LCID",
    # Large-cap cyclicals / defensives for breadth
    "JPM",
    "BAC",
    "GS",
    "MS",
    "C",
    "WFC",
    "AXP",
    "V",
    "MA",
    "UNH",
    "LLY",
    "JNJ",
    "PFE",
    "MRK",
    "ABBV",
    "TMO",
    "ISRG",
    "XOM",
    "CVX",
    "COP",
    "SLB",
    "OXY",
    "CAT",
    "DE",
    "GE",
    "BA",
    "LMT",
    "RTX",
    "COST",
    "WMT",
    "TGT",
    "HD",
    "LOW",
    "NKE",
    "SBUX",
    "MCD",
    # Major ETFs / thematic baskets
    "SPY",
    "QQQ",
    "IWM",
    "VOO",
    "DIA",
    "FBTC",
    "IBIT",
    "VOLT",
    "REMX",
    "XLE",
    "XLF",
    "XLK",
    "SMH",
    "SOXX",
    "ARKK",
    "KWEB",
]

ETF_TICKERS = {
    "SPY",
    "QQQ",
    "IWM",
    "VOO",
    "DIA",
    "FBTC",
    "IBIT",
    "VOLT",
    "REMX",
    "XLE",
    "XLF",
    "XLK",
    "SMH",
    "SOXX",
    "ARKK",
    "KWEB",
}

BROAD_MARKET_FALLBACK = """
A AAPL ABBV ABNB ABT ACGL ACN ADBE ADI ADM ADP ADSK AEE AEP AES AFL AIG AIZ AJG AKAM ALB ALGN ALL ALLE AMAT AMCR AMD AME AMGN AMP AMT AMZN ANET ANSS AON AOS APA APD APH APO APP APTV ARE ARM ATO AVB AVGO AVY AWK AXON AXP AZO
BA BAC BALL BAX BBY BDX BEN BF-B BG BIIB BK BKNG BKR BLK BMY BR BRK-B BRO BSX BWA BX BXP
C CAG CAH CARR CAT CB CBOE CBRE CCI CCL CDNS CDW CE CEG CF CFG CHD CHRW CHTR CI CINF CL CLX CMCSA CME CMG CMI CMS CNC CNP COF COIN COO COP COR COST CPAY CPRT CPT CRL CRM CRWD CSCO CSGP CSX CTAS CTLT CTRA CTSH CTVA CVS CVX CZR
D DAL DASH DD DE DELL DFS DG DGX DHI DHR DIS DLR DLTR DOC DOV DOW DPZ DRI DTE DUK DVA DVN DXCM
EA EBAY ECL ED EFX EG EIX EL ELV EMN EMR ENPH EOG EPAM EQIX EQR EQT ES ESS ETN ETSY EVRG EW EXC EXPD EXPE EXR
F FANG FAST FCX FDS FDX FE FFIV FI FICO FIS FITB FMC FOX FOXA FRT FSLR FTNT FTV
GD GE GEHC GEN GEV GILD GIS GL GLW GM GNRC GOOG GOOGL GPC GPN GRMN GS GWW
HAL HAS HBAN HCA HD HES HIG HII HLT HOLX HON HPE HPQ HRL HSIC HST HSY HUBB HUM HWM
IBM ICE IDXX IEX IFF ILMN INCY INTC INTU INVH IP IPG IQV IR IRM ISRG IT ITW IVZ
J JBHT JBL JCI JKHY JNJ JPM
K KDP KEY KEYS KHC KIM KKR KLAC KMB KMI KMX KO KR KVUE
L LDOS LEN LH LHX LIN LKQ LLY LMT LNT LOW LRCX LULU LVS LW LYB LYV
MA MAA MAR MAS MCD MCHP MCK MCO MDLZ MDT MET META MGM MHK MKC MKTX MLM MMC MMM MNST MO MOH MOS MPC MPWR MRK MRNA MRVL MS MSCI MSFT MSI MTB MTCH MTD MU NDAQ NDSN
NEE NEM NFLX NI NKE NOC NOW NRG NSC NTAP NTRS NUE NVDA NVR NWS NWSA
ODFL OKE OMC ON ORCL ORLY OTIS OXY
PANW PAYC PAYX PCAR PCG PEG PEP PFE PFG PG PGR PH PHM PKG PLD PLTR PM PNC PNR PNW PODD POOL PPG PPL PRU PSA PSX PTC PWR PYPL
QCOM QRVO
RCL REG REGN RF RHI RJF RL RMD ROK ROL ROP ROST RSG RTX RVTY
SBAC SBUX SCHW SHW SLB SMCI SNA SNPS SO SOLV SPG SPGI SRE STE STLD STT STX STZ SW SWK SWKS SYF SYK SYY
T TAP TDG TEL TER TFC TGT TJX TMO TMUS TPR TRGP TRMB TROW TRV TSCO TSLA TSN TT TTWO TXN TXT TYL
UAL UBER UDR UHS ULTA UNH UNP UPS URI USB
V VICI VLO VLTO VMC VRSK VRSN VRTX VST VTR VTRS VZ
W WAB WAT WBA WBD WDC WEC WELL WFC WM WMB WMT WRB WST WTW WY WYNN
XEL XOM XYL
YUM ZBH ZBRA ZTS
AA ACHR AFRM AI ALIT AMC AMPX APP ARKK ASTS ASML AVAV BBAI BE BLBD BROS CELH CHWY CLS CLSK CRSP CRWV CVNA DDOG DJT DKNG DOCN DUOL ENPH ETSY FBTC FSLY GME HOOD HIMS IBIT IONQ IREN JOBY KWEB LCID LUNR MARA MSTR NET NIO NU OKTA PATH PINS QBTS QQQ QUBT RBLX RDDT REMX RGTI RIOT RKLB RIVN ROKU SHOP SMH SOFI SOUN SOXX SPY SQ TSM TWLO UPST VOO VOLT XLE XLF XLK
""".split()

UNIVERSE_FILE_CANDIDATES = [
    Path("storage/us_listed_universe.csv"),
    Path("data/us_listed_universe.csv"),
]

EXCLUDED_SYMBOL_TOKENS = ("WARRANT", "WARRANTS", "UNIT", "UNITS", "RIGHT", "RIGHTS", "PREFERRED", "PREF")
EXCLUDED_SYMBOL_SUFFIXES = ("-W", "-WS", "-WT", "-U", "-R", ".W", ".WS", ".WT", ".U", ".R")


def _normalize_symbol(value: str) -> str:
    symbol = str(value or "").strip().upper().replace(".", "-")
    return "".join(ch for ch in symbol if ch.isalnum() or ch == "-")


def _is_common_share_symbol(symbol: str, name: str = "") -> bool:
    if not symbol or len(symbol) > 7:
        return False
    if any(symbol.endswith(suffix) for suffix in EXCLUDED_SYMBOL_SUFFIXES):
        return False
    upper_name = str(name or "").upper()
    if any(token in upper_name for token in EXCLUDED_SYMBOL_TOKENS):
        return False
    return True


def _load_local_universe_file() -> tuple[list[str], dict] | None:
    for path in UNIVERSE_FILE_CANDIDATES:
        if not path.exists():
            continue
        try:
            frame = pd.read_csv(path)
            symbol_column = next((col for col in frame.columns if str(col).lower() in {"symbol", "ticker", "ticker_symbol"}), frame.columns[0])
            name_column = next((col for col in frame.columns if str(col).lower() in {"name", "company", "company_name", "security name"}), None)
            symbols = []
            seen = set()
            for _, row in frame.iterrows():
                symbol = _normalize_symbol(row.get(symbol_column))
                name = str(row.get(name_column) or "") if name_column else ""
                if symbol and symbol not in seen and _is_common_share_symbol(symbol, name):
                    seen.add(symbol)
                    symbols.append(symbol)
            return symbols, {
                "universe_source": str(path),
                "universe_count": len(frame),
                "filtered_count": len(symbols),
                "status": "OK" if symbols else "Error",
                "message": "Loaded local listed-symbol universe." if symbols else "Local listed-symbol file had no usable symbols.",
            }
        except Exception as exc:
            return [], {
                "universe_source": str(path),
                "universe_count": 0,
                "filtered_count": 0,
                "status": "Error",
                "message": f"Could not read local listed-symbol universe: {exc}",
            }
    return None


def get_broad_market_universe(include_etfs: bool = False) -> list[str]:
    symbols, _ = get_broad_market_universe_with_status(include_etfs=include_etfs)
    return symbols


def get_broad_market_universe_with_status(include_etfs: bool = False) -> tuple[list[str], dict]:
    local = _load_local_universe_file()
    if local:
        symbols, status = local
    else:
        symbols = [_normalize_symbol(symbol) for symbol in BROAD_MARKET_FALLBACK]
        status = {
            "universe_source": "Bundled static broad liquid U.S. universe",
            "universe_count": len(BROAD_MARKET_FALLBACK),
            "filtered_count": 0,
            "status": "Fallback",
            "message": "Local listed-symbol universe file not found; using bundled broad liquid fallback.",
        }
    seen = set()
    output = []
    for symbol in symbols:
        if not _is_common_share_symbol(symbol):
            continue
        if not include_etfs and symbol in ETF_TICKERS:
            continue
        if symbol not in seen:
            seen.add(symbol)
            output.append(symbol)
    status = {
        **status,
        "filtered_count": len(output),
        "include_etfs": include_etfs,
    }
    return output, status

SOCIAL_MOMENTUM_UNIVERSE = [
    "NVDA",
    "TSLA",
    "PLTR",
    "SOFI",
    "HOOD",
    "MSTR",
    "COIN",
    "IONQ",
    "RGTI",
    "QBTS",
    "QUBT",
    "AMPX",
    "ASTS",
    "RKLB",
    "CRWV",
    "AI",
    "SOUN",
    "BBAI",
    "MARA",
    "RIOT",
    "GME",
    "AMC",
    "CVNA",
    "UPST",
    "AFRM",
]


def market_universe(include_etfs: bool = True, extra_tickers: list[str] | None = None) -> list[str]:
    seen = set()
    output = []
    for ticker in [*(extra_tickers or []), *CORE_MARKET_UNIVERSE]:
        symbol = str(ticker or "").strip().upper()
        if not symbol or symbol in seen:
            continue
        if not include_etfs and symbol in ETF_TICKERS:
            continue
        seen.add(symbol)
        output.append(symbol)
    return output
