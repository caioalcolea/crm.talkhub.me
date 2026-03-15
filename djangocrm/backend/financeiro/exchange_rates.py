"""
Exchange rate fetching with caching.

Primary: open.er-api.com (free, no API key)
Fallback: BCB PTAX (for BRL pairs)
Cache: Django cache (Redis) with 4h TTL.
"""
import datetime
import logging
from decimal import Decimal, ROUND_HALF_UP

import requests
from django.core.cache import cache

logger = logging.getLogger(__name__)

CACHE_TTL = 4 * 60 * 60  # 4 hours
REQUEST_TIMEOUT = 10  # seconds


class ExchangeRateError(Exception):
    """Raised when exchange rate cannot be fetched."""
    pass


def get_exchange_rate(from_currency, to_currency, date=None):
    """
    Get commercial exchange rate: 1 unit of from_currency = X units of to_currency.

    Args:
        from_currency: Source currency code (e.g. "USD")
        to_currency: Target currency code (e.g. "BRL")
        date: Optional date for historical rate (ignored for now, uses latest)

    Returns:
        Decimal: Exchange rate

    Raises:
        ExchangeRateError: If rate cannot be fetched from any source
    """
    if from_currency == to_currency:
        return Decimal("1")

    cache_key = f"exchange_rate:{from_currency}:{to_currency}"
    if date:
        cache_key += f":{date.isoformat()}"

    # Check cache
    cached = cache.get(cache_key)
    if cached is not None:
        return Decimal(str(cached))

    # Try primary API
    rate = None
    source = None

    try:
        rate = _fetch_er_api(from_currency, to_currency)
        source = "er-api"
    except Exception as e:
        logger.warning("er-api failed for %s→%s: %s", from_currency, to_currency, e)

    # Fallback: BCB PTAX (only works for pairs involving BRL)
    if rate is None and ("BRL" in (from_currency, to_currency)):
        try:
            rate = _fetch_bcb_ptax(from_currency, to_currency, date)
            source = "bcb-ptax"
        except Exception as e:
            logger.warning("BCB PTAX failed for %s→%s: %s", from_currency, to_currency, e)

    if rate is None:
        raise ExchangeRateError(
            f"Impossivel obter taxa de cambio {from_currency}→{to_currency}. "
            "Tente novamente mais tarde ou use taxa fixa."
        )

    # Round to 8 decimal places
    rate = rate.quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)

    # Cache it
    cache.set(cache_key, str(rate), CACHE_TTL)

    logger.info(
        "Exchange rate %s→%s = %s (source: %s)",
        from_currency, to_currency, rate, source,
    )
    return rate


def _fetch_er_api(from_currency, to_currency):
    """
    Fetch rate from open.er-api.com (free, no key required).
    Returns: Decimal rate (1 from_currency = X to_currency)
    """
    url = f"https://open.er-api.com/v6/latest/{from_currency}"
    resp = requests.get(url, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()

    if data.get("result") != "success":
        raise ExchangeRateError(f"er-api error: {data.get('error-type', 'unknown')}")

    rates = data.get("rates", {})
    if to_currency not in rates:
        raise ExchangeRateError(f"er-api: currency {to_currency} not found in rates")

    return Decimal(str(rates[to_currency]))


def _fetch_bcb_ptax(from_currency, to_currency, date=None):
    """
    Fetch rate from BCB PTAX API (Brazilian Central Bank).
    Only works for BRL ↔ foreign currency pairs.
    Returns: Decimal rate (1 from_currency = X to_currency)
    """
    # Determine the foreign currency (non-BRL side)
    if from_currency == "BRL":
        foreign = to_currency
        invert = True  # We need BRL→foreign, PTAX gives foreign→BRL
    elif to_currency == "BRL":
        foreign = from_currency
        invert = False  # We need foreign→BRL, which is what PTAX gives
    else:
        raise ExchangeRateError("BCB PTAX only works for BRL pairs")

    ref_date = date or datetime.date.today()
    # BCB uses MM-DD-YYYY format
    date_str = ref_date.strftime("%m-%d-%Y")
    # Search a 7-day window to handle weekends/holidays
    start = ref_date - datetime.timedelta(days=7)
    start_str = start.strftime("%m-%d-%Y")

    url = (
        "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
        f"CotacaoMoedaPeriodo(moeda=@moeda,dataInicial=@di,dataFinalCotacao=@df)"
        f"?@moeda='{foreign}'&@di='{start_str}'&@df='{date_str}'"
        "&$top=1&$orderby=dataHoraCotacao%20desc&$format=json"
    )

    resp = requests.get(url, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()

    values = data.get("value", [])
    if not values:
        raise ExchangeRateError(f"BCB PTAX: no data for {foreign} on {ref_date}")

    # cotacaoCompra = buy rate, cotacaoVenda = sell rate
    # Use sell rate (cotacaoVenda) as commercial rate
    rate_brl = Decimal(str(values[0]["cotacaoVenda"]))

    if invert:
        # BRL → foreign: 1 BRL = 1/rate_brl foreign
        return (Decimal("1") / rate_brl).quantize(
            Decimal("0.00000001"), rounding=ROUND_HALF_UP
        )
    else:
        # foreign → BRL: 1 foreign = rate_brl BRL
        return rate_brl
