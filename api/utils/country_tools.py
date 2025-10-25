from api.v1.models.country_data import CountryData
from api.v1.models.system_meta import SystemMeta
from PIL import Image, ImageDraw, ImageFont
import random, requests, os, io, boto3
from sqlalchemy.orm import Session
from datetime import datetime
from sqlalchemy import func
from urllib.parse import unquote


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

AWS_ACCESS_KEY_ID="0751eafbf6934156b3ba86fdef0a7d8f"
AWS_SECRET_ACCESS_KEY="d3b7c7f49aa71207ae977308d07a005b8f2cd35025208e823118e7d6cbd81d7a"

s3 = boto3.client(
    "s3",
    region_name="us-east-1",
    endpoint_url="https://objstorage.leapcell.io",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)

BUCKET_NAME = "os-wsp1980603830540251137-vs3x-yv5n-h4cxpsz2"
SUMMARY_KEY = "cache/summary.png"


def generate_summary_image(db):
    total_countries = db.query(func.count(CountryData.country_id)).scalar()
    top_countries = (
        db.query(CountryData.country_name, CountryData.estimated_gdp)
        .filter(CountryData.estimated_gdp.isnot(None))
        .order_by(CountryData.estimated_gdp.desc())
        .limit(5)
        .all()
    )
    last_refresh = (
        db.query(func.max(CountryData.last_refreshed_at)).scalar() or datetime.utcnow()
    )

    # --- Create the image ---
    img = Image.new("RGB", (800, 500), color=(240, 240, 240))
    draw = ImageDraw.Draw(img)

    try:
        font_title = ImageFont.truetype("arial.ttf", 28)
        font_text = ImageFont.truetype("arial.ttf", 20)
    except:
        font_title = font_text = None  # fallback if arial not found

    draw.text((50, 40), "🌍 Countries Summary", fill="black", font=font_title)
    draw.text(
        (50, 100), f"Total Countries: {total_countries}", fill="black", font=font_text
    )
    draw.text((50, 140), "Top 5 by Estimated GDP:", fill="black", font=font_text)

    y = 180
    for idx, (name, gdp) in enumerate(top_countries, start=1):
        draw.text((70, y), f"{idx}. {name} — {gdp:,.1f}", fill="black", font=font_text)
        y += 30

    draw.text(
        (50, y + 30),
        f"Last Refreshed: {last_refresh.isoformat()}Z",
        fill="gray",
        font=font_text,
    )

    # --- Upload cleanly to S3 ---
    with io.BytesIO() as output:
        img.save(output, format="PNG")
        output.seek(0)
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=SUMMARY_KEY, 
            Body=output.getvalue(),
            ContentType="image/png",
        )
    decoded_key = unquote(SUMMARY_KEY)
    return f"https://1xg7ah.leapcellobj.com/{BUCKET_NAME}/{decoded_key}"


def refresh_countries_data(db):
    countries_url = "https://restcountries.com/v2/all?fields=name,capital,region,population,flag,currencies"
    exchange_url = "https://open.er-api.com/v6/latest/USD"

    # Fetch data
    exchange_data = requests.get(exchange_url, timeout=10).json()
    rates = exchange_data.get("rates", {})
    country_data = requests.get(countries_url, timeout=10).json()

    cached_count = 0
    for c in country_data:
        name = c.get("name")
        capital = c.get("capital")
        region = c.get("region")
        population = c.get("population", 0)
        flag_url = c.get("flag")

        currencies = c.get("currencies", [])
        if not currencies:
            currency_code = None
            exchange_rate = None
            estimated_gdp = 0
        else:
            currency_code = currencies[0].get("code")
            if currency_code in rates:
                exchange_rate = rates[currency_code]
                estimated_gdp = round(
                    population * random.uniform(1000, 2000) / exchange_rate, 1
                )
            else:
                exchange_rate = None
                estimated_gdp = None

        # Case-insensitive match
        existing_country = (
            db.query(CountryData)
            .filter(func.lower(CountryData.country_name) == func.lower(name))
            .first()
        )

        if existing_country:
            existing_country.capital = capital
            existing_country.region = region
            existing_country.population = population
            existing_country.currency_code = currency_code
            existing_country.exchange_rate = exchange_rate
            existing_country.estimated_gdp = estimated_gdp
            existing_country.flag_url = flag_url
            existing_country.last_refreshed_at = datetime.utcnow()
        else:
            new_country = CountryData(
                country_name=name,
                capital=capital,
                region=region,
                population=population,
                currency_code=currency_code,
                exchange_rate=exchange_rate,
                estimated_gdp=estimated_gdp,
                flag_url=flag_url,
            )
            db.add(new_country)

        cached_count += 1

    # Update global timestamp
    meta = db.query(SystemMeta).filter(SystemMeta.key == "global_status").first()
    if not meta:
        meta = SystemMeta(
            key="global_status", value="active", last_refreshed_at=datetime.utcnow()
        )
        db.add(meta)
    else:
        meta.last_refreshed_at = datetime.utcnow()

    db.commit()

    # Generate summary image
    generate_summary_image(db)

    return cached_count
