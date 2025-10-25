from api.utils.country_tools import refresh_countries_data, s3, BUCKET_NAME, SUMMARY_KEY
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi import APIRouter, HTTPException, Depends, status, Query
from api.v1.models.country_data import CountryData
from api.db.database import get_db
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
import os

country_ops = APIRouter(tags=["Countries"])


@country_ops.post("/countries/refresh", status_code=status.HTTP_200_OK)
def refresh_countries_endpoint(db: Session = Depends(get_db)):
    """
    Fetch all countries and exchange rates, then cache them in the database.
    """
    try:
        total = refresh_countries_data(db)
        return {
            "message": "Countries data refreshed successfully.",
            "total_cached": total,
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@country_ops.get("/countries", status_code=status.HTTP_200_OK)
def get_all_countries(
    region: str | None = Query(None, description="Filter by region"),
    currency: str | None = Query(None, description="Filter by currency code"),
    sort: str | None = Query(None, description="Sort by GDP: gdp_asc or gdp_desc"),
    db: Session = Depends(get_db),

):
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

    if not countries:
        raise HTTPException(
            status_code=404, detail="No countries found matching criteria."
        )

    return {
        "results": countries,
    }

@country_ops.get("/countries/image", status_code=status.HTTP_200_OK)
def get_summary_image():
    try:
        s3.head_object(Bucket=BUCKET_NAME, Key=SUMMARY_KEY)
        # Redirect user to view the image directly
        return RedirectResponse(
            url=f"https://1xg7ah.leapcellobj.com/os-wsp1980603830540251137-vs3x-yv5n-h4cxpsz2/cache/summary.png"
        )
    except s3.exceptions.ClientError:
        return JSONResponse(
            status_code=404, content={"error": "Summary image not found"}
        )


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

    return country


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
