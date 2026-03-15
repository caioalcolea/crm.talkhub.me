"""
Currency codes and symbols for the Financeiro module.

Extends the CRM's base CURRENCY_CODES with cryptocurrency support.
Uses Decimal(18,8) for crypto values and Decimal(18,2) for converted fiat values.
"""

LANCAMENTO_TIPOS = (
    ("PAGAR", "Conta a Pagar"),
    ("RECEBER", "Conta a Receber"),
)

LANCAMENTO_STATUS = (
    ("ABERTO", "Aberto"),
    ("PAGO", "Pago"),
    ("CANCELADO", "Cancelado"),
)

PARCELA_STATUS = (
    ("ABERTO", "Aberto"),
    ("PAGO", "Pago"),
    ("CANCELADO", "Cancelado"),
)

EXCHANGE_RATE_TYPES = (
    ("FIXO", "Fixo"),
    ("VARIAVEL", "Variável"),
)

RECORRENCIA_TIPOS = (
    ("MENSAL", "Mensal"),
    ("QUINZENAL", "Quinzenal"),
    ("SEMANAL", "Semanal"),
    ("ANUAL", "Anual"),
)

# =============================================================================
# PIX / Payment Transaction
# =============================================================================

TRANSACTION_TYPES = (
    ("pix_qrcode", "PIX QR Code"),
    ("pix_manual", "PIX Manual"),
    ("gateway", "Gateway de Pagamento"),
)

TRANSACTION_STATUS = (
    ("pending", "Pendente"),
    ("confirmed", "Confirmado"),
    ("failed", "Falhou"),
    ("expired", "Expirado"),
    ("refunded", "Estornado"),
)


# Extended currency codes: 13 fiat + 8 crypto
FINANCEIRO_CURRENCY_CODES = (
    # Fiat currencies (from common/utils.py)
    ("USD", "USD - Dólar Americano"),
    ("EUR", "EUR - Euro"),
    ("GBP", "GBP - Libra Esterlina"),
    ("INR", "INR - Rupia Indiana"),
    ("CAD", "CAD - Dólar Canadense"),
    ("AUD", "AUD - Dólar Australiano"),
    ("JPY", "JPY - Iene"),
    ("CNY", "CNY - Yuan"),
    ("CHF", "CHF - Franco Suíço"),
    ("SGD", "SGD - Dólar de Singapura"),
    ("AED", "AED - Dirham"),
    ("BRL", "BRL - Real"),
    ("MXN", "MXN - Peso Mexicano"),
    # Cryptocurrencies
    ("BTC", "BTC - Bitcoin"),
    ("ETH", "ETH - Ethereum"),
    ("USDT", "USDT - Tether"),
    ("USDC", "USDC - USD Coin"),
    ("SOL", "SOL - Solana"),
    ("BNB", "BNB - Binance Coin"),
    ("XRP", "XRP - Ripple"),
    ("ADA", "ADA - Cardano"),
)

FINANCEIRO_CURRENCY_SYMBOLS = {
    # Fiat
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "INR": "₹",
    "CAD": "CA$",
    "AUD": "A$",
    "JPY": "¥",
    "CNY": "¥",
    "CHF": "CHF",
    "SGD": "S$",
    "AED": "د.إ",
    "BRL": "R$",
    "MXN": "MX$",
    # Crypto
    "BTC": "₿",
    "ETH": "Ξ",
    "USDT": "₮",
    "USDC": "USDC",
    "SOL": "◎",
    "BNB": "BNB",
    "XRP": "XRP",
    "ADA": "₳",
}

# Crypto currencies need 8 decimal places
CRYPTO_CURRENCIES = {"BTC", "ETH", "USDT", "USDC", "SOL", "BNB", "XRP", "ADA"}
