import dropbox.exceptions
import dropbox.files
from api.v1.models.country_data import CountryData
from fastapi import HTTPException, status
from dotenv import load_dotenv
from api.v1.models.system_meta import SystemMeta
from PIL import Image, ImageDraw, ImageFont
import random, requests, io, boto3, dropbox, os
from datetime import datetime
from sqlalchemy import func

load_dotenv(".env.config")

DROPBOX_ACCESS_TOKEN = os.getenv("DROPBOX_TOKEN")
DROPBOX_PATH = "/cache/summary.png"
dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)

def fetch_exchange_rate(base_url: str, currency_code: str) -> float:
    """
    Fetch exchange rate for a given currency from the external API.
    Returns the rate as a float or raises HTTPException(503) if unavailable.
    """
    try:
        response = requests.get(base_url, timeout=10)
        response.raise_for_status()
        data = response.json()

        rates = data.get("rates", {})
        rate = rates.get(currency_code)

        if rate is None:
            raise ValueError(f"Exchange rate for {currency_code} not found.")

        return rate

    except requests.exceptions.RequestException as e:
        # Any HTTP or timeout-related issue
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "External data source unavailable",
                "details": f"Could not fetch data from Exchange Rate API: {str(e)}",
            },
        )
    except Exception as e:
        # Catch-all for any unexpected issue
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "External data source unavailable",
                "details": f"Exchange Rate API error: {str(e)}",
            },
        )


def fetch_countries_data(countries_url: str, exchange_base_url: str):
    """
    Fetch all countries' data, attach exchange rate, and compute estimated GDP.
    Raises HTTP 503 if either external API fails or times out.
    """
    try:
        # --- Fetch Exchange Rates ---
        try:
            exchange_response = requests.get(exchange_base_url, timeout=10)
            exchange_response.raise_for_status()
            exchange_data = exchange_response.json()
            rates = exchange_data.get("rates", {})
        except requests.exceptions.RequestException as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "error": "External data source unavailable",
                    "details": f"Could not fetch data from Exchange Rate API: {str(e)}",
                },
            )

        # --- Fetch Countries Data ---
        try:
            country_response = requests.get(countries_url, timeout=10)
            country_response.raise_for_status()
            countries = country_response.json()
        except requests.exceptions.RequestException as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "error": "External data source unavailable",
                    "details": f"Could not fetch data from Countries API: {str(e)}",
                },
            )

        # --- Enrichment ---
        enriched_countries = []

        for c in countries:
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
                currency_code = currencies[0].get("code") if currencies[0] else None

                if currency_code in rates:
                    exchange_rate = rates[currency_code]
                    estimated_gdp = (
                        population * random.uniform(1000, 2000) / exchange_rate
                    )
                else:
                    exchange_rate = None
                    estimated_gdp = None

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

    except HTTPException:
        # Let FastAPI propagate the raised 503 error correctly
        raise
    except Exception as e:
        # Unexpected error (e.g., JSON parse issue)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "External data source unavailable",
                "details": f"Unexpected error while processing data: {str(e)}",
            },
        )


def generate_summary_image(db):
    """
    Generate a visual summary of country statistics and upload to Dropbox.
    """
    try:
        # --- Query Data ---
        total_countries = db.query(func.count(CountryData.country_id)).scalar()
        top_countries = (
            db.query(CountryData.country_name, CountryData.estimated_gdp)
            .filter(CountryData.estimated_gdp.isnot(None))
            .order_by(CountryData.estimated_gdp.desc())
            .limit(5)
            .all()
        )
        last_refresh = (
            db.query(func.max(CountryData.last_refreshed_at)).scalar()
            or datetime.utcnow()
        )

        # --- Create the image ---
        img = Image.new("RGB", (800, 500), color=(240, 240, 240))
        draw = ImageDraw.Draw(img)

        try:
            font_title = ImageFont.truetype("arial.ttf", 28)
            font_text = ImageFont.truetype("arial.ttf", 20)
        except:
            font_title = font_text = None  # fallback if Arial is missing

        draw.text((50, 40), "Countries Summary", fill="black", font=font_title)
        draw.text(
            (50, 100),
            f"Total Countries: {total_countries}",
            fill="black",
            font=font_text,
        )
        draw.text((50, 140), "Top 5 by Estimated GDP:", fill="black", font=font_text)

        y = 180
        for idx, (name, gdp) in enumerate(top_countries, start=1):
            draw.text(
                (70, y), f"{idx}. {name} — {gdp:,.1f}", fill="black", font=font_text
            )
            y += 30

        draw.text(
            (50, y + 30),
            f"Last Refreshed: {last_refresh.isoformat()}Z",
            fill="gray",
            font=font_text,
        )

        # --- Convert image to bytes ---
        image_bytes = io.BytesIO()
        img.save(image_bytes, format="PNG")
        image_bytes.seek(0)

        # --- Upload to Dropbox ---
        dbx.files_upload(
            image_bytes.read(),
            DROPBOX_PATH,
            mode=dropbox.files.WriteMode("overwrite"),
            mute=True,
        )

        # --- Create or retrieve a shareable link ---
        try:
            shared_link_metadata = dbx.sharing_create_shared_link_with_settings(
                DROPBOX_PATH
            )
            shared_url = shared_link_metadata.url.replace("?dl=0", "?raw=1")
        except dropbox.exceptions.ApiError:
            # If link already exists, retrieve it
            links = dbx.sharing_list_shared_links(path=DROPBOX_PATH).links
            if not links:
                raise
            shared_url = links[0].url.replace("?dl=0", "?raw=1")

        return {"summary_image_url": shared_url}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Failed to generate or upload summary image",
                "details": str(e),
            },
        )


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
