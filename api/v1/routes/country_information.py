from api.utils.country_tools import refresh_countries_data, dbx, DROPBOX_ACCESS_TOKEN, DROPBOX_PATH
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, HTTPException, Depends, status, Query
from api.v1.models.country_data import CountryData
from api.db.database import get_db, get_async_db
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
import httpx, requests, io

country_ops = APIRouter(tags=["Countries"])


@country_ops.post("/countries/refresh", status_code=status.HTTP_200_OK)
async def refresh_countries_endpoint(db: AsyncSession = Depends(get_async_db)):
    """
    Asynchronously fetches all countries and exchange rates, then updates or caches
    them in the database.
    """
    try:
        total = await refresh_countries_data(db)
        return {
            "message": "Countries data refreshed successfully.",
            "total_cached": total,
        }

    except HTTPException as e:
        # Pass through known FastAPI exceptions
        raise e

    except Exception as e:
        # Handle unexpected errors gracefully
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh countries data: {str(e)}",
        )


@country_ops.get("/countries", status_code=status.HTTP_200_OK)
def get_all_countries(
    region: str | None = Query(None, description="Filter by region"),
    currency: str | None = Query(None, description="Filter by currency code"),
    sort: str | None = Query(None, description="Sort by GDP: gdp_asc or gdp_desc"),
    db: Session = Depends(get_db),
):
    # --- Base Query ---
    query = db.query(CountryData)

    # --- Filters ---
    if region:
        query = query.filter(CountryData.region.ilike(f"%{region}%"))
    if currency:
        query = query.filter(CountryData.currency_code == currency)

    # --- Sorting ---
    if sort == "gdp_asc":
        query = query.order_by(CountryData.estimated_gdp.asc())
    elif sort == "gdp_desc":
        query = query.order_by(desc(CountryData.estimated_gdp))
    else:
        query = query.order_by(CountryData.country_name.asc())

    countries = query.all()

    # --- Error Handling ---
    if not countries:
        raise HTTPException(
            status_code=404, detail="No countries found matching criteria."
        )

    # --- Response Formatting ---
    response = []
    for country in countries:
        response.append({
            "id": country.country_id,
            "name": country.country_name,
            "capital": country.capital,
            "region": country.region,
            "population": country.population,
            "currency_code": country.currency_code,
            "exchange_rate": country.exchange_rate,
            "estimated_gdp": country.estimated_gdp,
            "flag_url": country.flag_url,
            "last_refreshed_at": country.last_refreshed_at
        })

    return response


@country_ops.get("/countries/image", status_code=status.HTTP_200_OK)
def get_summary_image():
    try:
        dbx.files_get_metadata(DROPBOX_PATH)
        links = dbx.sharing_list_shared_links(path=DROPBOX_PATH).links
        if not links:
            return JSONResponse(status_code=404, content={"error": "Image not found"})

        shared_url = links[0].url.replace("?dl=0", "?raw=1")

        # Fetch the image bytes
        response = requests.get(shared_url)
        if response.status_code != 200:
            raise HTTPException(status_code=404, detail="Image not accessible")

        # Stream the actual image data
        return StreamingResponse(
            io.BytesIO(response.content),
            media_type="image/png",  # or "image/jpeg" depending on your file
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@country_ops.get("/countries/{name}", status_code=status.HTTP_200_OK)
def get_country_by_name(name: str, db: Session = Depends(get_db)):
    """
    Retrieve a specific country by its name (case-insensitive).
    """
    country = (
        db.query(CountryData)
        .filter(CountryData.country_name.ilike(f"%{name}%"))
        .first()
    )
    if not country:
        raise HTTPException(status_code=404, detail=f"Country '{name}' not found.")

    return {
        "id": country.country_id,
        "name": country.country_name,
        "capital": country.capital,
        "region": country.region,
        "population": country.population,
        "currency_code": country.currency_code,
        "exchange_rate": country.exchange_rate,
        "estimated_gdp": country.estimated_gdp,
        "flag_url": country.flag_url,
        "last_refreshed_at": country.last_refreshed_at
    }


@country_ops.delete("/countries/{name}", status_code=status.HTTP_200_OK)
def delete_country(name: str, db: Session = Depends(get_db)):
    """
    Delete a country record by name.
    """
    country = (
        db.query(CountryData)
        .filter(CountryData.country_name.ilike(f"%{name}%"))
        .first()
    )

    if not country:
        raise HTTPException(status_code=404, detail=f"Country '{name}' not found.")

    db.delete(country)
    db.commit()

    return {"message": f"Country '{country.country_name}' deleted successfully."}

@country_ops.get("/status", status_code=status.HTTP_200_OK)
def get_status(db: Session = Depends(get_db)):
    """
    Return total countries and the most recent refresh timestamp.
    """
    total_countries = db.query(func.count(CountryData.country_id)).scalar()

    last_refresh = db.query(func.max(CountryData.last_refreshed_at)).scalar()

    return {
        "total_countries": total_countries or 0,
        "last_refreshed_at": (last_refresh.isoformat() + "Z" if last_refresh else None),
    }
