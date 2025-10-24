import random, requests

countries_url = "https://restcountries.com/v2/all?fields=name,capital,region,population,flag,currencies"
exchange_url = "https://open.er-api.com/v6/latest/USD"


def fetch_exchange_rate(base_url: str, currency_code: str) -> float:
    try:
        response = requests.get(base_url, timeout=10)
        response.raise_for_status()
        data = response.json()

        rates = data.get("rates", {})
        rate = rates.get(currency_code)

        if rate is None:
            raise ValueError(f"Exchange rate for {currency_code} not found.")

        return rate

    except Exception as e:
        print(f"[Exchange rate Error]: {e}")
        return None


def fetch_countries_data(countries_url: str, exchange_base_url: str):
    """
    Fetch all countries' data, attach exchange rate, and compute estimated GDP
    according to the given currency-handling rules.
    """
    try:
        # Fetch all exchange rates once
        exchange_response = requests.get(exchange_base_url, timeout=10)
        exchange_response.raise_for_status()
        exchange_data = exchange_response.json()
        rates = exchange_data.get("rates", {})

        # Fetch all countries
        country_response = requests.get(countries_url, timeout=10)
        country_response.raise_for_status()
        countries = country_response.json()

        enriched_countries = []

        for c in countries:
            name = c.get("name")
            capital = c.get("capital")
            region = c.get("region")
            population = c.get("population", 0)
            flag_url = c.get("flag")

            # --- Handle Currency Rules ---
            currencies = c.get("currencies", [])
            if not currencies:  # case: no currencies
                currency_code = None
                exchange_rate = None
                estimated_gdp = 0

            else:
                currency_code = currencies[0].get("code") if currencies[0] else None

                if currency_code in rates:  # valid currency found
                    exchange_rate = rates[currency_code]
                    estimated_gdp = (
                        population * random.uniform(1000, 2000) / exchange_rate
                    )
                else:  # currency not found in rates
                    exchange_rate = None
                    estimated_gdp = None

            # Collect final record
            enriched_countries.append(
                {
                    "name": name,
                    "capital": capital,
                    "region": region,
                    "population": population,
                    "currency_code": currency_code,
                    "exchange_rate": exchange_rate,
                    "estimated_gdp": estimated_gdp,
                    "flag_url": flag_url,
                }
            )

        return enriched_countries

    except Exception as e:
        print(f"[Country Fetch Error]: {e}")
        return []


#data = fetch_countries_data(countries_url, exchange_url)
#print(data[0])  # Prints one country's enriched info
