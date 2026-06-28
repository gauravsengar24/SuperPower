"""Ticker universe — loads US, European, and Indian stocks
with full company names. Tries external CSVs first, falls back to
built-in list of 500+ major tickers if downloads fail.

Cached locally at ~/.trading/ticker_cache.json (refreshed daily).
"""

import csv
import io
import json
import logging
import re
import time
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger(__name__)

CACHE_PATH = Path("~/.trading/ticker_cache.json").expanduser()
CACHE_TTL_HOURS = 24

NASDAQ_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
NYSE_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"
OTC_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/otclisted.txt"
NSE_EQUITY_URL = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
EURONEXT_URL = "https://live.euronext.com/sites/default/files/stock-list/Euronext_Equities_All.csv"
LSE_URL = "https://www.londonstockexchange.com/sites/default/files/csv/LSEEquities.csv"

FALLBACK_TICKERS = [
    {"ticker": "AAPL", "name": "Apple Inc.", "exchange": "NASDAQ"},
    {"ticker": "MSFT", "name": "Microsoft Corporation", "exchange": "NASDAQ"},
    {"ticker": "GOOGL", "name": "Alphabet Inc.", "exchange": "NASDAQ"},
    {"ticker": "AMZN", "name": "Amazon.com Inc.", "exchange": "NASDAQ"},
    {"ticker": "NVDA", "name": "NVIDIA Corporation", "exchange": "NASDAQ"},
    {"ticker": "META", "name": "Meta Platforms Inc.", "exchange": "NASDAQ"},
    {"ticker": "TSLA", "name": "Tesla Inc.", "exchange": "NASDAQ"},
    {"ticker": "BRK.B", "name": "Berkshire Hathaway Inc.", "exchange": "NYSE"},
    {"ticker": "JPM", "name": "JPMorgan Chase & Co.", "exchange": "NYSE"},
    {"ticker": "V", "name": "Visa Inc.", "exchange": "NYSE"},
    {"ticker": "JNJ", "name": "Johnson & Johnson", "exchange": "NYSE"},
    {"ticker": "WMT", "name": "Walmart Inc.", "exchange": "NYSE"},
    {"ticker": "MA", "name": "Mastercard Inc.", "exchange": "NYSE"},
    {"ticker": "PG", "name": "Procter & Gamble Co.", "exchange": "NYSE"},
    {"ticker": "UNH", "name": "UnitedHealth Group Inc.", "exchange": "NYSE"},
    {"ticker": "HD", "name": "Home Depot Inc.", "exchange": "NYSE"},
    {"ticker": "DIS", "name": "Walt Disney Co.", "exchange": "NYSE"},
    {"ticker": "BAC", "name": "Bank of America Corp.", "exchange": "NYSE"},
    {"ticker": "ADBE", "name": "Adobe Inc.", "exchange": "NASDAQ"},
    {"ticker": "CRM", "name": "Salesforce Inc.", "exchange": "NYSE"},
    {"ticker": "NFLX", "name": "Netflix Inc.", "exchange": "NASDAQ"},
    {"ticker": "CMCSA", "name": "Comcast Corp.", "exchange": "NASDAQ"},
    {"ticker": "XOM", "name": "Exxon Mobil Corp.", "exchange": "NYSE"},
    {"ticker": "VZ", "name": "Verizon Communications Inc.", "exchange": "NYSE"},
    {"ticker": "KO", "name": "Coca-Cola Co.", "exchange": "NYSE"},
    {"ticker": "PEP", "name": "PepsiCo Inc.", "exchange": "NASDAQ"},
    {"ticker": "INTC", "name": "Intel Corp.", "exchange": "NASDAQ"},
    {"ticker": "AMD", "name": "Advanced Micro Devices Inc.", "exchange": "NASDAQ"},
    {"ticker": "PYPL", "name": "PayPal Holdings Inc.", "exchange": "NASDAQ"},
    {"ticker": "UBER", "name": "Uber Technologies Inc.", "exchange": "NYSE"},
    {"ticker": "SQ", "name": "Block Inc.", "exchange": "NYSE"},
    {"ticker": "SNAP", "name": "Snap Inc.", "exchange": "NYSE"},
    {"ticker": "SHOP", "name": "Shopify Inc.", "exchange": "NYSE"},
    {"ticker": "ZM", "name": "Zoom Video Communications Inc.", "exchange": "NASDAQ"},
    {"ticker": "DASH", "name": "DoorDash Inc.", "exchange": "NYSE"},
    {"ticker": "ABNB", "name": "Airbnb Inc.", "exchange": "NASDAQ"},
    {"ticker": "COIN", "name": "Coinbase Global Inc.", "exchange": "NASDAQ"},
    {"ticker": "PLTR", "name": "Palantir Technologies Inc.", "exchange": "NYSE"},
    {"ticker": "RIVN", "name": "Rivian Automotive Inc.", "exchange": "NASDAQ"},
    {"ticker": "LCID", "name": "Lucid Group Inc.", "exchange": "NASDAQ"},
    {"ticker": "SPY", "name": "SPDR S&P 500 ETF Trust", "exchange": "NYSE"},
    {"ticker": "QQQ", "name": "Invesco QQQ Trust", "exchange": "NASDAQ"},
    {"ticker": "IWM", "name": "iShares Russell 2000 ETF", "exchange": "NYSE"},
    {"ticker": "DIA", "name": "SPDR Dow Jones Industrial Average ETF", "exchange": "NYSE"},
    {"ticker": "TLT", "name": "iShares 20+ Year Treasury Bond ETF", "exchange": "NASDAQ"},
    {"ticker": "GLD", "name": "SPDR Gold Trust", "exchange": "NYSE"},
    {"ticker": "SLV", "name": "iShares Silver Trust", "exchange": "NYSE"},
    {"ticker": "USO", "name": "United States Oil Fund", "exchange": "NYSE"},
    {"ticker": "AAL", "name": "American Airlines Group Inc.", "exchange": "NASDAQ"},
    {"ticker": "AAP", "name": "Advance Auto Parts Inc.", "exchange": "NYSE"},
    {"ticker": "ABBV", "name": "AbbVie Inc.", "exchange": "NYSE"},
    {"ticker": "ABNB", "name": "Airbnb Inc.", "exchange": "NASDAQ"},
    {"ticker": "ABT", "name": "Abbott Laboratories", "exchange": "NYSE"},
    {"ticker": "ACN", "name": "Accenture plc", "exchange": "NYSE"},
    {"ticker": "ADBE", "name": "Adobe Inc.", "exchange": "NASDAQ"},
    {"ticker": "ADM", "name": "Archer-Daniels-Midland Co.", "exchange": "NYSE"},
    {"ticker": "ADP", "name": "Automatic Data Processing Inc.", "exchange": "NASDAQ"},
    {"ticker": "AEP", "name": "American Electric Power Co.", "exchange": "NASDAQ"},
    {"ticker": "AES", "name": "AES Corp.", "exchange": "NYSE"},
    {"ticker": "AFL", "name": "Aflac Inc.", "exchange": "NYSE"},
    {"ticker": "AIG", "name": "American International Group Inc.", "exchange": "NYSE"},
    {"ticker": "AIZ", "name": "Assurant Inc.", "exchange": "NYSE"},
    {"ticker": "AJG", "name": "Arthur J. Gallagher & Co.", "exchange": "NYSE"},
    {"ticker": "AKAM", "name": "Akamai Technologies Inc.", "exchange": "NASDAQ"},
    {"ticker": "ALB", "name": "Albemarle Corp.", "exchange": "NYSE"},
    {"ticker": "ALGN", "name": "Align Technology Inc.", "exchange": "NASDAQ"},
    {"ticker": "ALL", "name": "Allstate Corp.", "exchange": "NYSE"},
    {"ticker": "ALLE", "name": "Allegion plc", "exchange": "NYSE"},
    {"ticker": "AMAT", "name": "Applied Materials Inc.", "exchange": "NASDAQ"},
    {"ticker": "AMCR", "name": "Amcor plc", "exchange": "NYSE"},
    {"ticker": "AMD", "name": "Advanced Micro Devices Inc.", "exchange": "NASDAQ"},
    {"ticker": "AME", "name": "AMETEK Inc.", "exchange": "NYSE"},
    {"ticker": "AMGN", "name": "Amgen Inc.", "exchange": "NASDAQ"},
    {"ticker": "AMP", "name": "Ameriprise Financial Inc.", "exchange": "NYSE"},
    {"ticker": "AMT", "name": "American Tower Corp.", "exchange": "NYSE"},
    {"ticker": "AMZN", "name": "Amazon.com Inc.", "exchange": "NASDAQ"},
    {"ticker": "ANET", "name": "Arista Networks Inc.", "exchange": "NYSE"},
    {"ticker": "ANSS", "name": "ANSYS Inc.", "exchange": "NASDAQ"},
    {"ticker": "AON", "name": "Aon plc", "exchange": "NYSE"},
    {"ticker": "AOS", "name": "A. O. Smith Corp.", "exchange": "NYSE"},
    {"ticker": "APA", "name": "APA Corp.", "exchange": "NASDAQ"},
    {"ticker": "APD", "name": "Air Products and Chemicals Inc.", "exchange": "NYSE"},
    {"ticker": "APH", "name": "Amphenol Corp.", "exchange": "NYSE"},
    {"ticker": "APO", "name": "Apollo Global Management Inc.", "exchange": "NYSE"},
    {"ticker": "APP", "name": "AppLovin Corp.", "exchange": "NASDAQ"},
    {"ticker": "APTV", "name": "Aptiv plc", "exchange": "NYSE"},
    {"ticker": "ARE", "name": "Alexandria Real Estate Equities Inc.", "exchange": "NYSE"},
    {"ticker": "ATO", "name": "Atmos Energy Corp.", "exchange": "NYSE"},
    {"ticker": "AVB", "name": "AvalonBay Communities Inc.", "exchange": "NYSE"},
    {"ticker": "AVGO", "name": "Broadcom Inc.", "exchange": "NASDAQ"},
    {"ticker": "AVY", "name": "Avery Dennison Corp.", "exchange": "NYSE"},
    {"ticker": "AWK", "name": "American Water Works Co.", "exchange": "NYSE"},
    {"ticker": "AXON", "name": "Axon Enterprise Inc.", "exchange": "NASDAQ"},
    {"ticker": "AXP", "name": "American Express Co.", "exchange": "NYSE"},
    {"ticker": "AZO", "name": "AutoZone Inc.", "exchange": "NYSE"},
    {"ticker": "BA", "name": "Boeing Co.", "exchange": "NYSE"},
    {"ticker": "BALL", "name": "Ball Corp.", "exchange": "NYSE"},
    {"ticker": "BAX", "name": "Baxter International Inc.", "exchange": "NYSE"},
    {"ticker": "BBY", "name": "Best Buy Co.", "exchange": "NYSE"},
    {"ticker": "BDX", "name": "Becton Dickinson and Co.", "exchange": "NYSE"},
    {"ticker": "BEN", "name": "Franklin Resources Inc.", "exchange": "NYSE"},
    {"ticker": "BF.B", "name": "Brown-Forman Corp.", "exchange": "NYSE"},
    {"ticker": "BG", "name": "Bunge Global SA", "exchange": "NYSE"},
    {"ticker": "BIIB", "name": "Biogen Inc.", "exchange": "NASDAQ"},
    {"ticker": "BIO", "name": "Bio-Rad Laboratories Inc.", "exchange": "NYSE"},
    {"ticker": "BK", "name": "Bank of New York Mellon Corp.", "exchange": "NYSE"},
    {"ticker": "BKNG", "name": "Booking Holdings Inc.", "exchange": "NASDAQ"},
    {"ticker": "BKR", "name": "Baker Hughes Co.", "exchange": "NASDAQ"},
    {"ticker": "BLK", "name": "BlackRock Inc.", "exchange": "NYSE"},
    {"ticker": "BMY", "name": "Bristol-Myers Squibb Co.", "exchange": "NYSE"},
    {"ticker": "BR", "name": "Broadridge Financial Solutions Inc.", "exchange": "NYSE"},
    {"ticker": "BRO", "name": "Brown & Brown Inc.", "exchange": "NYSE"},
    {"ticker": "BSX", "name": "Boston Scientific Corp.", "exchange": "NYSE"},
    {"ticker": "BWA", "name": "BorgWarner Inc.", "exchange": "NYSE"},
    {"ticker": "BX", "name": "Blackstone Inc.", "exchange": "NYSE"},
    {"ticker": "BXP", "name": "Boston Properties Inc.", "exchange": "NYSE"},
    {"ticker": "C", "name": "Citigroup Inc.", "exchange": "NYSE"},
    {"ticker": "CAG", "name": "Conagra Brands Inc.", "exchange": "NYSE"},
    {"ticker": "CAH", "name": "Cardinal Health Inc.", "exchange": "NYSE"},
    {"ticker": "CARR", "name": "Carrier Global Corp.", "exchange": "NYSE"},
    {"ticker": "CAT", "name": "Caterpillar Inc.", "exchange": "NYSE"},
    {"ticker": "CB", "name": "Chubb Ltd.", "exchange": "NYSE"},
    {"ticker": "CBOE", "name": "Cboe Global Markets Inc.", "exchange": "NYSE"},
    {"ticker": "CBRE", "name": "CBRE Group Inc.", "exchange": "NYSE"},
    {"ticker": "CCL", "name": "Carnival Corp.", "exchange": "NYSE"},
    {"ticker": "CDNS", "name": "Cadence Design Systems Inc.", "exchange": "NASDAQ"},
    {"ticker": "CDW", "name": "CDW Corp.", "exchange": "NASDAQ"},
    {"ticker": "CE", "name": "Celanese Corp.", "exchange": "NYSE"},
    {"ticker": "CELH", "name": "Celsius Holdings Inc.", "exchange": "NASDAQ"},
    {"ticker": "CF", "name": "CF Industries Holdings Inc.", "exchange": "NYSE"},
    {"ticker": "CFG", "name": "Citizens Financial Group Inc.", "exchange": "NYSE"},
    {"ticker": "CHD", "name": "Church & Dwight Co.", "exchange": "NYSE"},
    {"ticker": "CHRW", "name": "C.H. Robinson Worldwide Inc.", "exchange": "NASDAQ"},
    {"ticker": "CHTR", "name": "Charter Communications Inc.", "exchange": "NASDAQ"},
    {"ticker": "CI", "name": "Cigna Group", "exchange": "NYSE"},
    {"ticker": "CINF", "name": "Cincinnati Financial Corp.", "exchange": "NASDAQ"},
    {"ticker": "CL", "name": "Colgate-Palmolive Co.", "exchange": "NYSE"},
    {"ticker": "CLX", "name": "Clorox Co.", "exchange": "NYSE"},
    {"ticker": "CME", "name": "CME Group Inc.", "exchange": "NASDAQ"},
    {"ticker": "CMG", "name": "Chipotle Mexican Grill Inc.", "exchange": "NYSE"},
    {"ticker": "CMI", "name": "Cummins Inc.", "exchange": "NYSE"},
    {"ticker": "CMS", "name": "CMS Energy Corp.", "exchange": "NYSE"},
    {"ticker": "CNC", "name": "Centene Corp.", "exchange": "NYSE"},
    {"ticker": "CNP", "name": "CenterPoint Energy Inc.", "exchange": "NYSE"},
    {"ticker": "COF", "name": "Capital One Financial Corp.", "exchange": "NYSE"},
    {"ticker": "COST", "name": "Costco Wholesale Corp.", "exchange": "NASDAQ"},
    {"ticker": "CPAY", "name": "Corpay Inc.", "exchange": "NYSE"},
    {"ticker": "CPB", "name": "Campbell's Co.", "exchange": "NYSE"},
    {"ticker": "CPRT", "name": "Copart Inc.", "exchange": "NASDAQ"},
    {"ticker": "CPT", "name": "Camden Property Trust", "exchange": "NYSE"},
    {"ticker": "CRL", "name": "Charles River Laboratories Intl.", "exchange": "NYSE"},
    {"ticker": "CRM", "name": "Salesforce Inc.", "exchange": "NYSE"},
    {"ticker": "CRWD", "name": "CrowdStrike Holdings Inc.", "exchange": "NASDAQ"},
    {"ticker": "CSCO", "name": "Cisco Systems Inc.", "exchange": "NASDAQ"},
    {"ticker": "CSGP", "name": "CoStar Group Inc.", "exchange": "NASDAQ"},
    {"ticker": "CSX", "name": "CSX Corp.", "exchange": "NASDAQ"},
    {"ticker": "CTAS", "name": "Cintas Corp.", "exchange": "NASDAQ"},
    {"ticker": "CTRA", "name": "Coterra Energy Inc.", "exchange": "NYSE"},
    {"ticker": "CTSH", "name": "Cognizant Technology Solutions", "exchange": "NASDAQ"},
    {"ticker": "CTVA", "name": "Corteva Inc.", "exchange": "NYSE"},
    {"ticker": "CVS", "name": "CVS Health Corp.", "exchange": "NYSE"},
    {"ticker": "CVX", "name": "Chevron Corp.", "exchange": "NYSE"},
    {"ticker": "D", "name": "Dominion Energy Inc.", "exchange": "NYSE"},
    {"ticker": "DAL", "name": "Delta Air Lines Inc.", "exchange": "NYSE"},
    {"ticker": "DAY", "name": "Dayforce Inc.", "exchange": "NYSE"},
    {"ticker": "DD", "name": "DuPont de Nemours Inc.", "exchange": "NYSE"},
    {"ticker": "DDOG", "name": "Datadog Inc.", "exchange": "NASDAQ"},
    {"ticker": "DE", "name": "Deere & Co.", "exchange": "NYSE"},
    {"ticker": "DECK", "name": "Deckers Outdoor Corp.", "exchange": "NYSE"},
    {"ticker": "DELL", "name": "Dell Technologies Inc.", "exchange": "NYSE"},
    {"ticker": "DFS", "name": "Discover Financial Services", "exchange": "NYSE"},
    {"ticker": "DG", "name": "Dollar General Corp.", "exchange": "NYSE"},
    {"ticker": "DGX", "name": "Quest Diagnostics Inc.", "exchange": "NYSE"},
    {"ticker": "DHI", "name": "D.R. Horton Inc.", "exchange": "NYSE"},
    {"ticker": "DHR", "name": "Danaher Corp.", "exchange": "NYSE"},
    {"ticker": "DIS", "name": "Walt Disney Co.", "exchange": "NYSE"},
    {"ticker": "DLR", "name": "Digital Realty Trust Inc.", "exchange": "NYSE"},
    {"ticker": "DLTR", "name": "Dollar Tree Inc.", "exchange": "NASDAQ"},
    {"ticker": "DOV", "name": "Dover Corp.", "exchange": "NYSE"},
    {"ticker": "DOW", "name": "Dow Inc.", "exchange": "NYSE"},
    {"ticker": "DPZ", "name": "Domino's Pizza Inc.", "exchange": "NYSE"},
    {"ticker": "DRI", "name": "Darden Restaurants Inc.", "exchange": "NYSE"},
    {"ticker": "DTE", "name": "DTE Energy Co.", "exchange": "NYSE"},
    {"ticker": "DUK", "name": "Duke Energy Corp.", "exchange": "NYSE"},
    {"ticker": "DVA", "name": "DaVita Inc.", "exchange": "NYSE"},
    {"ticker": "DVN", "name": "Devon Energy Corp.", "exchange": "NYSE"},
    {"ticker": "DXCM", "name": "DexCom Inc.", "exchange": "NASDAQ"},
    {"ticker": "EA", "name": "Electronic Arts Inc.", "exchange": "NASDAQ"},
    {"ticker": "EBAY", "name": "eBay Inc.", "exchange": "NASDAQ"},
    {"ticker": "ECL", "name": "Ecolab Inc.", "exchange": "NYSE"},
    {"ticker": "ED", "name": "Consolidated Edison Inc.", "exchange": "NYSE"},
    {"ticker": "EFX", "name": "Equifax Inc.", "exchange": "NYSE"},
    {"ticker": "EG", "name": "Everest Group Ltd.", "exchange": "NYSE"},
    {"ticker": "EIX", "name": "Edison International", "exchange": "NYSE"},
    {"ticker": "EL", "name": "Estee Lauder Cos.", "exchange": "NYSE"},
    {"ticker": "EMN", "name": "Eastman Chemical Co.", "exchange": "NYSE"},
    {"ticker": "EMR", "name": "Emerson Electric Co.", "exchange": "NYSE"},
    {"ticker": "ENPH", "name": "Enphase Energy Inc.", "exchange": "NASDAQ"},
    {"ticker": "EOG", "name": "EOG Resources Inc.", "exchange": "NYSE"},
    {"ticker": "EPAM", "name": "Epam Systems Inc.", "exchange": "NYSE"},
    {"ticker": "EQIX", "name": "Equinix Inc.", "exchange": "NYSE"},
    {"ticker": "EQR", "name": "Equity Residential", "exchange": "NYSE"},
    {"ticker": "ERIE", "name": "Erie Indemnity Co.", "exchange": "NASDAQ"},
    {"ticker": "ES", "name": "Eversource Energy", "exchange": "NYSE"},
    {"ticker": "ESS", "name": "Essex Property Trust Inc.", "exchange": "NYSE"},
    {"ticker": "ETN", "name": "Eaton Corp.", "exchange": "NYSE"},
    {"ticker": "ETR", "name": "Entergy Corp.", "exchange": "NYSE"},
    {"ticker": "ETSY", "name": "Etsy Inc.", "exchange": "NASDAQ"},
    {"ticker": "EVRG", "name": "Evergy Inc.", "exchange": "NYSE"},
    {"ticker": "EW", "name": "Edwards Lifesciences Corp.", "exchange": "NYSE"},
    {"ticker": "EXC", "name": "Exelon Corp.", "exchange": "NASDAQ"},
    {"ticker": "EXPD", "name": "Expeditors International of WA", "exchange": "NASDAQ"},
    {"ticker": "EXPE", "name": "Expedia Group Inc.", "exchange": "NASDAQ"},
    {"ticker": "EXR", "name": "Extra Space Storage Inc.", "exchange": "NYSE"},
    {"ticker": "F", "name": "Ford Motor Co.", "exchange": "NYSE"},
    {"ticker": "FANG", "name": "Diamondback Energy Inc.", "exchange": "NASDAQ"},
    {"ticker": "FAST", "name": "Fastenal Co.", "exchange": "NASDAQ"},
    {"ticker": "FCX", "name": "Freeport-McMoRan Inc.", "exchange": "NYSE"},
    {"ticker": "FDS", "name": "FactSet Research Systems Inc.", "exchange": "NYSE"},
    {"ticker": "FDX", "name": "FedEx Corp.", "exchange": "NYSE"},
    {"ticker": "FE", "name": "FirstEnergy Corp.", "exchange": "NYSE"},
    {"ticker": "FFIV", "name": "F5 Inc.", "exchange": "NASDAQ"},
    {"ticker": "FI", "name": "Fiserv Inc.", "exchange": "NYSE"},
    {"ticker": "FICO", "name": "Fair Isaac Corp.", "exchange": "NYSE"},
    {"ticker": "FIS", "name": "Fidelity National Info Services", "exchange": "NYSE"},
    {"ticker": "FITB", "name": "Fifth Third Bancorp", "exchange": "NASDAQ"},
    {"ticker": "FMC", "name": "FMC Corp.", "exchange": "NYSE"},
    {"ticker": "FOX", "name": "Fox Corp.", "exchange": "NASDAQ"},
    {"ticker": "FOXA", "name": "Fox Corp.", "exchange": "NASDAQ"},
    {"ticker": "FRT", "name": "Federal Realty Investment Trust", "exchange": "NYSE"},
    {"ticker": "FSLR", "name": "First Solar Inc.", "exchange": "NASDAQ"},
    {"ticker": "FTNT", "name": "Fortinet Inc.", "exchange": "NASDAQ"},
    {"ticker": "FTV", "name": "Fortive Corp.", "exchange": "NYSE"},
    {"ticker": "GD", "name": "General Dynamics Corp.", "exchange": "NYSE"},
    {"ticker": "GE", "name": "General Electric Co.", "exchange": "NYSE"},
    {"ticker": "GEHC", "name": "GE HealthCare Technologies Inc.", "exchange": "NASDAQ"},
    {"ticker": "GEN", "name": "Gen Digital Inc.", "exchange": "NASDAQ"},
    {"ticker": "GDDY", "name": "GoDaddy Inc.", "exchange": "NYSE"},
    {"ticker": "GILD", "name": "Gilead Sciences Inc.", "exchange": "NASDAQ"},
    {"ticker": "GIS", "name": "General Mills Inc.", "exchange": "NYSE"},
    {"ticker": "GL", "name": "Globe Life Inc.", "exchange": "NYSE"},
    {"ticker": "GLW", "name": "Corning Inc.", "exchange": "NYSE"},
    {"ticker": "GM", "name": "General Motors Co.", "exchange": "NYSE"},
    {"ticker": "GNRC", "name": "Generac Holdings Inc.", "exchange": "NYSE"},
    {"ticker": "GOOG", "name": "Alphabet Inc.", "exchange": "NASDAQ"},
    {"ticker": "GPC", "name": "Genuine Parts Co.", "exchange": "NYSE"},
    {"ticker": "GPN", "name": "Global Payments Inc.", "exchange": "NYSE"},
    {"ticker": "GRMN", "name": "Garmin Ltd.", "exchange": "NYSE"},
    {"ticker": "GS", "name": "Goldman Sachs Group Inc.", "exchange": "NYSE"},
    {"ticker": "GWW", "name": "W.W. Grainger Inc.", "exchange": "NYSE"},
    {"ticker": "HAL", "name": "Halliburton Co.", "exchange": "NYSE"},
    {"ticker": "HAS", "name": "Hasbro Inc.", "exchange": "NASDAQ"},
    {"ticker": "HBAN", "name": "Huntington Bancshares Inc.", "exchange": "NASDAQ"},
    {"ticker": "HCA", "name": "HCA Healthcare Inc.", "exchange": "NYSE"},
    {"ticker": "HD", "name": "Home Depot Inc.", "exchange": "NYSE"},
    {"ticker": "HEI", "name": "Heico Corp.", "exchange": "NYSE"},
    {"ticker": "HES", "name": "Hess Corp.", "exchange": "NYSE"},
    {"ticker": "HIG", "name": "Hartford Financial Services Group", "exchange": "NYSE"},
    {"ticker": "HII", "name": "Huntington Ingalls Industries Inc.", "exchange": "NYSE"},
    {"ticker": "HLT", "name": "Hilton Worldwide Holdings Inc.", "exchange": "NYSE"},
    {"ticker": "HOLX", "name": "Hologic Inc.", "exchange": "NASDAQ"},
    {"ticker": "HON", "name": "Honeywell International Inc.", "exchange": "NASDAQ"},
    {"ticker": "HPE", "name": "Hewlett Packard Enterprise Co.", "exchange": "NYSE"},
    {"ticker": "HPQ", "name": "HP Inc.", "exchange": "NYSE"},
    {"ticker": "HRL", "name": "Hormel Foods Corp.", "exchange": "NYSE"},
    {"ticker": "HSIC", "name": "Henry Schein Inc.", "exchange": "NASDAQ"},
    {"ticker": "HST", "name": "Host Hotels & Resorts Inc.", "exchange": "NASDAQ"},
    {"ticker": "HSY", "name": "Hershey Co.", "exchange": "NYSE"},
    {"ticker": "HUBB", "name": "Hubbell Inc.", "exchange": "NYSE"},
    {"ticker": "HUM", "name": "Humana Inc.", "exchange": "NYSE"},
    {"ticker": "HWM", "name": "Howmet Aerospace Inc.", "exchange": "NYSE"},
    {"ticker": "IBM", "name": "International Business Machines", "exchange": "NYSE"},
    {"ticker": "ICE", "name": "Intercontinental Exchange Inc.", "exchange": "NYSE"},
    {"ticker": "IDXX", "name": "IDEXX Laboratories Inc.", "exchange": "NASDAQ"},
    {"ticker": "IEX", "name": "IDEX Corp.", "exchange": "NYSE"},
    {"ticker": "IFF", "name": "International Flavors & Fragrances", "exchange": "NYSE"},
    {"ticker": "INCY", "name": "Incyte Corp.", "exchange": "NASDAQ"},
    {"ticker": "INTC", "name": "Intel Corp.", "exchange": "NASDAQ"},
    {"ticker": "INTU", "name": "Intuit Inc.", "exchange": "NASDAQ"},
    {"ticker": "INVH", "name": "Invitation Homes Inc.", "exchange": "NYSE"},
    {"ticker": "IP", "name": "International Paper Co.", "exchange": "NYSE"},
    {"ticker": "IPG", "name": "Interpublic Group of Cos.", "exchange": "NYSE"},
    {"ticker": "IQV", "name": "IQVIA Holdings Inc.", "exchange": "NYSE"},
    {"ticker": "IR", "name": "Ingersoll Rand Inc.", "exchange": "NYSE"},
    {"ticker": "IRM", "name": "Iron Mountain Inc.", "exchange": "NYSE"},
    {"ticker": "ISRG", "name": "Intuitive Surgical Inc.", "exchange": "NASDAQ"},
    {"ticker": "IT", "name": "Gartner Inc.", "exchange": "NYSE"},
    {"ticker": "ITW", "name": "Illinois Tool Works Inc.", "exchange": "NYSE"},
    {"ticker": "IVZ", "name": "Invesco Ltd.", "exchange": "NYSE"},
    {"ticker": "J", "name": "Jacobs Solutions Inc.", "exchange": "NYSE"},
    {"ticker": "JBHT", "name": "J.B. Hunt Transport Services Inc.", "exchange": "NASDAQ"},
    {"ticker": "JBL", "name": "Jabil Inc.", "exchange": "NYSE"},
    {"ticker": "JCI", "name": "Johnson Controls International plc", "exchange": "NYSE"},
    {"ticker": "JKHY", "name": "Jack Henry & Associates Inc.", "exchange": "NASDAQ"},
    {"ticker": "JNPR", "name": "Juniper Networks Inc.", "exchange": "NYSE"},
    {"ticker": "JPM", "name": "JPMorgan Chase & Co.", "exchange": "NYSE"},
    {"ticker": "K", "name": "Kellanova", "exchange": "NYSE"},
    {"ticker": "KDP", "name": "Keurig Dr Pepper Inc.", "exchange": "NASDAQ"},
    {"ticker": "KEY", "name": "KeyCorp", "exchange": "NYSE"},
    {"ticker": "KEYS", "name": "Keysight Technologies Inc.", "exchange": "NYSE"},
    {"ticker": "KHC", "name": "Kraft Heinz Co.", "exchange": "NASDAQ"},
    {"ticker": "KIM", "name": "Kimco Realty Corp.", "exchange": "NYSE"},
    {"ticker": "KKR", "name": "KKR & Co. Inc.", "exchange": "NYSE"},
    {"ticker": "KMB", "name": "Kimberly-Clark Corp.", "exchange": "NYSE"},
    {"ticker": "KMI", "name": "Kinder Morgan Inc.", "exchange": "NYSE"},
    {"ticker": "KMX", "name": "CarMax Inc.", "exchange": "NYSE"},
    {"ticker": "KO", "name": "Coca-Cola Co.", "exchange": "NYSE"},
    {"ticker": "KR", "name": "Kroger Co.", "exchange": "NYSE"},
    {"ticker": "KVUE", "name": "Kenvue Inc.", "exchange": "NYSE"},
    {"ticker": "L", "name": "Loews Corp.", "exchange": "NYSE"},
    {"ticker": "LDOS", "name": "Leidos Holdings Inc.", "exchange": "NYSE"},
    {"ticker": "LEN", "name": "Lennar Corp.", "exchange": "NYSE"},
    {"ticker": "LH", "name": "Labcorp Holdings Inc.", "exchange": "NYSE"},
    {"ticker": "LHX", "name": "L3Harris Technologies Inc.", "exchange": "NYSE"},
    {"ticker": "LIN", "name": "Linde plc", "exchange": "NYSE"},
    {"ticker": "LKQ", "name": "LKQ Corp.", "exchange": "NASDAQ"},
    {"ticker": "LLY", "name": "Eli Lilly and Co.", "exchange": "NYSE"},
    {"ticker": "LMT", "name": "Lockheed Martin Corp.", "exchange": "NYSE"},
    {"ticker": "LNC", "name": "Lincoln National Corp.", "exchange": "NYSE"},
    {"ticker": "LNT", "name": "Alliant Energy Corp.", "exchange": "NASDAQ"},
    {"ticker": "LOW", "name": "Lowe's Cos.", "exchange": "NYSE"},
    {"ticker": "LRCX", "name": "Lam Research Corp.", "exchange": "NASDAQ"},
    {"ticker": "LULU", "name": "Lululemon Athletica Inc.", "exchange": "NASDAQ"},
    {"ticker": "LUV", "name": "Southwest Airlines Co.", "exchange": "NYSE"},
    {"ticker": "LVS", "name": "Las Vegas Sands Corp.", "exchange": "NYSE"},
    {"ticker": "LW", "name": "Lamb Weston Holdings Inc.", "exchange": "NYSE"},
    {"ticker": "LYB", "name": "LyondellBasell Industries NV", "exchange": "NYSE"},
    {"ticker": "LYV", "name": "Live Nation Entertainment Inc.", "exchange": "NYSE"},
    {"ticker": "MA", "name": "Mastercard Inc.", "exchange": "NYSE"},
    {"ticker": "MAA", "name": "Mid-America Apartment Communities", "exchange": "NYSE"},
    {"ticker": "MANH", "name": "Manhattan Associates Inc.", "exchange": "NASDAQ"},
    {"ticker": "MAR", "name": "Marriott International Inc.", "exchange": "NASDAQ"},
    {"ticker": "MAS", "name": "Masco Corp.", "exchange": "NYSE"},
    {"ticker": "MCD", "name": "McDonald's Corp.", "exchange": "NYSE"},
    {"ticker": "MCHP", "name": "Microchip Technology Inc.", "exchange": "NASDAQ"},
    {"ticker": "MCK", "name": "McKesson Corp.", "exchange": "NYSE"},
    {"ticker": "MCO", "name": "Moody's Corp.", "exchange": "NYSE"},
    {"ticker": "MDLZ", "name": "Mondelez International Inc.", "exchange": "NASDAQ"},
    {"ticker": "MDT", "name": "Medtronic plc", "exchange": "NYSE"},
    {"ticker": "MET", "name": "MetLife Inc.", "exchange": "NYSE"},
    {"ticker": "META", "name": "Meta Platforms Inc.", "exchange": "NASDAQ"},
    {"ticker": "MGM", "name": "MGM Resorts International", "exchange": "NYSE"},
    {"ticker": "MKC", "name": "McCormick & Co.", "exchange": "NYSE"},
    {"ticker": "MKTX", "name": "MarketAxess Holdings Inc.", "exchange": "NASDAQ"},
    {"ticker": "MLM", "name": "Martin Marietta Materials Inc.", "exchange": "NYSE"},
    {"ticker": "MMC", "name": "Marsh & McLennan Cos.", "exchange": "NYSE"},
    {"ticker": "MMM", "name": "3M Co.", "exchange": "NYSE"},
    {"ticker": "MNST", "name": "Monster Beverage Corp.", "exchange": "NASDAQ"},
    {"ticker": "MO", "name": "Altria Group Inc.", "exchange": "NYSE"},
    {"ticker": "MOH", "name": "Molina Healthcare Inc.", "exchange": "NYSE"},
    {"ticker": "MOS", "name": "Mosaic Co.", "exchange": "NYSE"},
    {"ticker": "MPC", "name": "Marathon Petroleum Corp.", "exchange": "NYSE"},
    {"ticker": "MPWR", "name": "Monolithic Power Systems Inc.", "exchange": "NASDAQ"},
    {"ticker": "MRK", "name": "Merck & Co.", "exchange": "NYSE"},
    {"ticker": "MRNA", "name": "Moderna Inc.", "exchange": "NASDAQ"},
    {"ticker": "MRO", "name": "Marathon Oil Corp.", "exchange": "NYSE"},
    {"ticker": "MS", "name": "Morgan Stanley", "exchange": "NYSE"},
    {"ticker": "MSCI", "name": "MSCI Inc.", "exchange": "NYSE"},
    {"ticker": "MSFT", "name": "Microsoft Corporation", "exchange": "NASDAQ"},
    {"ticker": "MSI", "name": "Motorola Solutions Inc.", "exchange": "NYSE"},
    {"ticker": "MTB", "name": "M&T Bank Corp.", "exchange": "NYSE"},
    {"ticker": "MTCH", "name": "Match Group Inc.", "exchange": "NASDAQ"},
    {"ticker": "MTD", "name": "Mettler-Toledo International Inc.", "exchange": "NYSE"},
    {"ticker": "MU", "name": "Micron Technology Inc.", "exchange": "NASDAQ"},
    {"ticker": "NDAQ", "name": "Nasdaq Inc.", "exchange": "NASDAQ"},
    {"ticker": "NDSN", "name": "Nordson Corp.", "exchange": "NASDAQ"},
    {"ticker": "NEE", "name": "NextEra Energy Inc.", "exchange": "NYSE"},
    {"ticker": "NEM", "name": "Newmont Corp.", "exchange": "NYSE"},
    {"ticker": "NFLX", "name": "Netflix Inc.", "exchange": "NASDAQ"},
    {"ticker": "NI", "name": "NiSource Inc.", "exchange": "NYSE"},
    {"ticker": "NKE", "name": "Nike Inc.", "exchange": "NYSE"},
    {"ticker": "NOC", "name": "Northrop Grumman Corp.", "exchange": "NYSE"},
    {"ticker": "NOW", "name": "ServiceNow Inc.", "exchange": "NYSE"},
    {"ticker": "NRG", "name": "NRG Energy Inc.", "exchange": "NYSE"},
    {"ticker": "NSC", "name": "Norfolk Southern Corp.", "exchange": "NYSE"},
    {"ticker": "NTAP", "name": "NetApp Inc.", "exchange": "NASDAQ"},
    {"ticker": "NTRS", "name": "Northern Trust Corp.", "exchange": "NASDAQ"},
    {"ticker": "NUE", "name": "Nucor Corp.", "exchange": "NYSE"},
    {"ticker": "NVDA", "name": "NVIDIA Corporation", "exchange": "NASDAQ"},
    {"ticker": "NVR", "name": "NVR Inc.", "exchange": "NYSE"},
    {"ticker": "O", "name": "Realty Income Corp.", "exchange": "NYSE"},
    {"ticker": "ODFL", "name": "Old Dominion Freight Line Inc.", "exchange": "NASDAQ"},
    {"ticker": "OKE", "name": "ONEOK Inc.", "exchange": "NYSE"},
    {"ticker": "OMC", "name": "Omnicom Group Inc.", "exchange": "NYSE"},
    {"ticker": "ON", "name": "ON Semiconductor Corp.", "exchange": "NASDAQ"},
    {"ticker": "ORCL", "name": "Oracle Corp.", "exchange": "NYSE"},
    {"ticker": "ORLY", "name": "O'Reilly Automotive Inc.", "exchange": "NASDAQ"},
    {"ticker": "OTIS", "name": "Otis Worldwide Corp.", "exchange": "NYSE"},
    {"ticker": "OXY", "name": "Occidental Petroleum Corp.", "exchange": "NYSE"},
    {"ticker": "PANW", "name": "Palo Alto Networks Inc.", "exchange": "NASDAQ"},
    {"ticker": "PARA", "name": "Paramount Global", "exchange": "NASDAQ"},
    {"ticker": "PAYC", "name": "Paycom Software Inc.", "exchange": "NYSE"},
    {"ticker": "PAYX", "name": "Paychex Inc.", "exchange": "NASDAQ"},
    {"ticker": "PCAR", "name": "PACCAR Inc.", "exchange": "NASDAQ"},
    {"ticker": "PCG", "name": "PG&E Corp.", "exchange": "NYSE"},
    {"ticker": "PEG", "name": "Public Service Enterprise Group", "exchange": "NYSE"},
    {"ticker": "PEP", "name": "PepsiCo Inc.", "exchange": "NASDAQ"},
    {"ticker": "PFG", "name": "Principal Financial Group Inc.", "exchange": "NASDAQ"},
    {"ticker": "PG", "name": "Procter & Gamble Co.", "exchange": "NYSE"},
    {"ticker": "PGR", "name": "Progressive Corp.", "exchange": "NYSE"},
    {"ticker": "PH", "name": "Parker-Hannifin Corp.", "exchange": "NYSE"},
    {"ticker": "PHM", "name": "PulteGroup Inc.", "exchange": "NYSE"},
    {"ticker": "PINS", "name": "Pinterest Inc.", "exchange": "NYSE"},
    {"ticker": "PKG", "name": "Packaging Corp. of America", "exchange": "NYSE"},
    {"ticker": "PLD", "name": "Prologis Inc.", "exchange": "NYSE"},
    {"ticker": "PLTR", "name": "Palantir Technologies Inc.", "exchange": "NYSE"},
    {"ticker": "PM", "name": "Philip Morris International Inc.", "exchange": "NYSE"},
    {"ticker": "PNC", "name": "PNC Financial Services Group Inc.", "exchange": "NYSE"},
    {"ticker": "PNR", "name": "Pentair plc", "exchange": "NYSE"},
    {"ticker": "POOL", "name": "Pool Corp.", "exchange": "NASDAQ"},
    {"ticker": "PPG", "name": "PPG Industries Inc.", "exchange": "NYSE"},
    {"ticker": "PPL", "name": "PPL Corp.", "exchange": "NYSE"},
    {"ticker": "PRU", "name": "Prudential Financial Inc.", "exchange": "NYSE"},
    {"ticker": "PSA", "name": "Public Storage", "exchange": "NYSE"},
    {"ticker": "PSX", "name": "Phillips 66", "exchange": "NYSE"},
    {"ticker": "PWR", "name": "Quanta Services Inc.", "exchange": "NYSE"},
    {"ticker": "PYPL", "name": "PayPal Holdings Inc.", "exchange": "NASDAQ"},
    {"ticker": "QCOM", "name": "Qualcomm Inc.", "exchange": "NASDAQ"},
    {"ticker": "QRVO", "name": "Qorvo Inc.", "exchange": "NASDAQ"},
    {"ticker": "RCL", "name": "Royal Caribbean Cruises Ltd.", "exchange": "NYSE"},
    {"ticker": "REG", "name": "Regency Centers Corp.", "exchange": "NASDAQ"},
    {"ticker": "REGN", "name": "Regeneron Pharmaceuticals Inc.", "exchange": "NASDAQ"},
    {"ticker": "RF", "name": "Regions Financial Corp.", "exchange": "NYSE"},
    {"ticker": "RJF", "name": "Raymond James Financial Inc.", "exchange": "NYSE"},
    {"ticker": "RL", "name": "Ralph Lauren Corp.", "exchange": "NYSE"},
    {"ticker": "RMD", "name": "ResMed Inc.", "exchange": "NYSE"},
    {"ticker": "ROK", "name": "Rockwell Automation Inc.", "exchange": "NYSE"},
    {"ticker": "ROL", "name": "Rollins Inc.", "exchange": "NYSE"},
    {"ticker": "ROP", "name": "Roper Technologies Inc.", "exchange": "NYSE"},
    {"ticker": "ROST", "name": "Ross Stores Inc.", "exchange": "NASDAQ"},
    {"ticker": "RRC", "name": "Range Resources Corp.", "exchange": "NYSE"},
    {"ticker": "RS", "name": "Reliance Steel & Aluminum Co.", "exchange": "NYSE"},
    {"ticker": "RSG", "name": "Republic Services Inc.", "exchange": "NYSE"},
    {"ticker": "RTX", "name": "RTX Corp.", "exchange": "NYSE"},
    {"ticker": "RVTY", "name": "Revvity Inc.", "exchange": "NYSE"},
    {"ticker": "SAP.DE", "name": "SAP SE", "exchange": "XETRA"},
    {"ticker": "SIE.DE", "name": "Siemens AG", "exchange": "XETRA"},
    {"ticker": "ALV.DE", "name": "Allianz SE", "exchange": "XETRA"},
    {"ticker": "DBK.DE", "name": "Deutsche Bank AG", "exchange": "XETRA"},
    {"ticker": "BAS.DE", "name": "BASF SE", "exchange": "XETRA"},
    {"ticker": "BAYN.DE", "name": "Bayer AG", "exchange": "XETRA"},
    {"ticker": "BMW.DE", "name": "Bayerische Motoren Werke AG", "exchange": "XETRA"},
    {"ticker": "VOW3.DE", "name": "Volkswagen AG", "exchange": "XETRA"},
    {"ticker": "ADS.DE", "name": "Adidas AG", "exchange": "XETRA"},
    {"ticker": "MRK.DE", "name": "Merck KGaA", "exchange": "XETRA"},
    {"ticker": "MC.PA", "name": "LVMH Moet Hennessy Louis Vuitton SE", "exchange": "EURONEXT"},
    {"ticker": "OR.PA", "name": "L'Oreal SA", "exchange": "EURONEXT"},
    {"ticker": "TTE.PA", "name": "TotalEnergies SE", "exchange": "EURONEXT"},
    {"ticker": "SAN.PA", "name": "Sanofi SA", "exchange": "EURONEXT"},
    {"ticker": "AI.PA", "name": "Airbus SE", "exchange": "EURONEXT"},
    {"ticker": "SU.PA", "name": "Schneider Electric SE", "exchange": "EURONEXT"},
    {"ticker": "RMS.PA", "name": "Hermes International SA", "exchange": "EURONEXT"},
    {"ticker": "ULVR.L", "name": "Unilever plc", "exchange": "LSE"},
    {"ticker": "AZN.L", "name": "AstraZeneca plc", "exchange": "LSE"},
    {"ticker": "SHEL.L", "name": "Shell plc", "exchange": "LSE"},
    {"ticker": "HSBA.L", "name": "HSBC Holdings plc", "exchange": "LSE"},
    {"ticker": "BP.L", "name": "BP plc", "exchange": "LSE"},
    {"ticker": "GSK.L", "name": "GSK plc", "exchange": "LSE"},
    {"ticker": "ASML.AS", "name": "ASML Holding NV", "exchange": "EURONEXT"},
    {"ticker": "ADYEN.AS", "name": "Adyen NV", "exchange": "EURONEXT"},
    {"ticker": "INGA.AS", "name": "ING Groep NV", "exchange": "EURONEXT"},
    {"ticker": "NOVO-B.CO", "name": "Novo Nordisk A/S", "exchange": "OMXCOP"},
    {"ticker": "NESN.SW", "name": "Nestle SA", "exchange": "SIX"},
    {"ticker": "NOVN.SW", "name": "Novartis AG", "exchange": "SIX"},
    {"ticker": "ROG.SW", "name": "Roche Holding AG", "exchange": "SIX"},
    {"ticker": "UBSG.SW", "name": "UBS Group AG", "exchange": "SIX"},
    {"ticker": "RELIANCE.NS", "name": "Reliance Industries Ltd", "exchange": "NSE"},
    {"ticker": "TCS.NS", "name": "Tata Consultancy Services Ltd", "exchange": "NSE"},
    {"ticker": "HDFCBANK.NS", "name": "HDFC Bank Ltd", "exchange": "NSE"},
    {"ticker": "INFY.NS", "name": "Infosys Ltd", "exchange": "NSE"},
    {"ticker": "ICICIBANK.NS", "name": "ICICI Bank Ltd", "exchange": "NSE"},
    {"ticker": "BHARTIARTL.NS", "name": "Bharti Airtel Ltd", "exchange": "NSE"},
    {"ticker": "SBIN.NS", "name": "State Bank of India", "exchange": "NSE"},
    {"ticker": "WIPRO.NS", "name": "Wipro Ltd", "exchange": "NSE"},
    {"ticker": "HCLTECH.NS", "name": "HCL Technologies Ltd", "exchange": "NSE"},
    {"ticker": "LT.NS", "name": "Larsen & Toubro Ltd", "exchange": "NSE"},
    {"ticker": "HINDUNILVR.NS", "name": "Hindustan Unilever Ltd", "exchange": "NSE"},
    {"ticker": "ITC.NS", "name": "ITC Ltd", "exchange": "NSE"},
    {"ticker": "BAJFINANCE.NS", "name": "Bajaj Finance Ltd", "exchange": "NSE"},
    {"ticker": "ASIANPAINT.NS", "name": "Asian Paints Ltd", "exchange": "NSE"},
    {"ticker": "MARUTI.NS", "name": "Maruti Suzuki India Ltd", "exchange": "NSE"},
    {"ticker": "SUNPHARMA.NS", "name": "Sun Pharmaceutical Industries Ltd", "exchange": "NSE"},
    {"ticker": "TATAMOTORS.NS", "name": "Tata Motors Ltd", "exchange": "NSE"},
    {"ticker": "AXISBANK.NS", "name": "Axis Bank Ltd", "exchange": "NSE"},
    {"ticker": "KOTAKBANK.NS", "name": "Kotak Mahindra Bank Ltd", "exchange": "NSE"},
    {"ticker": "NTPC.NS", "name": "NTPC Ltd", "exchange": "NSE"},
    {"ticker": "ADANIENT.NS", "name": "Adani Enterprises Ltd", "exchange": "NSE"},
    {"ticker": "TATASTEEL.NS", "name": "Tata Steel Ltd", "exchange": "NSE"},
    {"ticker": "TITAN.NS", "name": "Titan Company Ltd", "exchange": "NSE"},
    {"ticker": "ULTRACEMCO.NS", "name": "UltraTech Cement Ltd", "exchange": "NSE"},
    {"ticker": "PIDILITIND.NS", "name": "Pidilite Industries Ltd", "exchange": "NSE"},
    {"ticker": "M&M.NS", "name": "Mahindra & Mahindra Ltd", "exchange": "NSE"},
]


def _download_csv(url: str, skip_rows: int = 0) -> list[dict]:
    try:
        resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        text = resp.text
        for _ in range(skip_rows):
            first_nl = text.find("\n")
            if first_nl == -1:
                return []
            text = text[first_nl + 1:]
        reader = csv.DictReader(io.StringIO(text))
        return [row for row in reader if any(v.strip() for v in row.values())]
    except Exception as e:
        logger.warning("Failed to download %s: %s", url, e)
        return []


def _load_nasdaq() -> list[dict]:
    rows = _download_csv(NASDAQ_URL)
    result = []
    for r in rows:
        symbol = r.get("Symbol", "").strip()
        name = r.get("Security Name", "").strip()
        if symbol and name:
            name = re.sub(r"\s*-\s*Common Stock.*", "", name, flags=re.IGNORECASE)
            name = re.sub(r"\s*-\s*Class [A-Z].*", "", name, flags=re.IGNORECASE)
            result.append({"ticker": symbol, "name": name.strip(), "exchange": "NASDAQ"})
    return result


def _load_nyse() -> list[dict]:
    rows = _download_csv(NYSE_URL)
    result = []
    for r in rows:
        symbol = r.get("ACT Symbol", "").strip()
        name = r.get("Company Name", "").strip()
        exchange = r.get("Exchange", "").strip()
        if symbol and name:
            result.append({"ticker": symbol, "name": name, "exchange": exchange or "NYSE"})
    return result


def _load_otc() -> list[dict]:
    rows = _download_csv(OTC_URL)
    result = []
    for r in rows:
        symbol = r.get("Symbol", "").strip()
        name = r.get("Company Name", "").strip()
        market = r.get("Market Category", "").strip()
        if symbol and name:
            result.append({"ticker": symbol, "name": name, "exchange": f"OTC {market}".strip() or "OTC"})
    return result


def _load_nse() -> list[dict]:
    rows = _download_csv(NSE_EQUITY_URL, skip_rows=1)
    result = []
    for r in rows:
        symbol = r.get("SYMBOL", "").strip()
        name = r.get("NAME OF COMPANY", "").strip()
        if symbol and name:
            result.append({"ticker": f"{symbol}.NS", "name": name, "exchange": "NSE"})
    return result


def _load_euronext() -> list[dict]:
    rows = _download_csv(EURONEXT_URL)
    result = []
    for r in rows:
        symbol = r.get("Symbol", "") or r.get("Code", "")
        name = r.get("Name", "") or r.get("Company name", "")
        market = r.get("Market", "") or "Euronext"
        if symbol and name:
            sym_clean = symbol.strip().replace(" ", "-")
            suffix = (
                ".PA" if "Paris" in market
                else ".AS" if "Amsterdam" in market
                else ".BR" if "Brussels" in market
                else ".LI" if "Lisbon" in market
                else ".OL" if "Oslo" in market
                else ".IR" if "Dublin" in market
                else ""
            )
            result.append({"ticker": f"{sym_clean}{suffix}", "name": name.strip(), "exchange": market.strip()})
    return result


def _load_lse() -> list[dict]:
    rows = _download_csv(LSE_URL)
    result = []
    for r in rows:
        symbol = r.get("TIDM", "") or r.get("Symbol", "")
        name = r.get("Company Name", "") or r.get("Name", "")
        if symbol and name:
            result.append({"ticker": f"{symbol.strip()}.L", "name": name.strip(), "exchange": "LSE"})
    return result


def _load_cache() -> Optional[list[dict]]:
    if CACHE_PATH.exists():
        try:
            data = json.loads(CACHE_PATH.read_text())
            age = time.time() - data.get("ts", 0)
            if age < CACHE_TTL_HOURS * 3600:
                return data.get("tickers", [])
        except (json.JSONDecodeError, KeyError):
            pass
    return None


def _save_cache(tickers: list[dict]):
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps({"ts": time.time(), "tickers": tickers}, indent=2))


def get_all_tickers(force_refresh: bool = False) -> list[dict]:
    if not force_refresh:
        cached = _load_cache()
        if cached:
            logger.info("Loaded %d tickers from cache", len(cached))
            return cached

    tickers = []
    any_success = False
    for loader, label in [
        (_load_nasdaq, "NASDAQ"),
        (_load_nyse, "NYSE"),
        (_load_otc, "OTC"),
        (_load_nse, "NSE"),
        (_load_euronext, "Euronext"),
        (_load_lse, "LSE"),
    ]:
        try:
            batch = loader()
            if batch:
                any_success = True
            logger.info("Loaded %d tickers from %s", len(batch), label)
            tickers.extend(batch)
        except Exception as e:
            logger.warning("Failed to load %s: %s", label, e)

    if not any_success:
        logger.warning("All downloads failed — using built-in fallback (%d tickers)", len(FALLBACK_TICKERS))
        tickers = FALLBACK_TICKERS[:]

    seen = set()
    unique = []
    for t in tickers:
        key = t["ticker"].upper()
        if key not in seen:
            seen.add(key)
            unique.append(t)

    unique.sort(key=lambda x: x["ticker"])
    logger.info("Total unique tickers: %d", len(unique))

    try:
        _save_cache(unique)
    except Exception as e:
        logger.warning("Failed to save ticker cache: %s", e)

    return unique


def search_tickers(query: str, max_results: int = 50) -> list[dict]:
    all_tickers = get_all_tickers()
    q = query.upper().strip()
    if not q:
        return all_tickers[:max_results]
    results = []
    for t in all_tickers:
        if q in t["ticker"].upper() or q in t["name"].upper():
            results.append(t)
            if len(results) >= max_results:
                break
    if not results:
        results = [t for t in all_tickers[:20]]
    return results


def format_ticker_display(item: dict) -> str:
    return f"{item['ticker']} — {item['name']} ({item.get('exchange', '')})"
