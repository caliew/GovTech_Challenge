import json
import logging

logger = logging.getLogger("APITools")

# A mock external database simulating an API server for Data.gov.sg CPI indices
MOCK_API_CPI_REGIONAL = {
    "Southeast Asia Average Inflation": {
        2020: 1.5,
        2021: 2.2,
        2022: 4.8,
        2023: 3.9,
        2024: 2.8
    },
    "Global Tech Talent Index": {
        2020: 100.0,
        2021: 112.5,
        2022: 124.0,
        2023: 119.5,  # Layoff correction
        2024: 125.8
    }
}

def fetch_regional_inflation_api(year_str: str) -> str:
    """
    Simulates fetching regional Southeast Asia average inflation rates from a external government API.
    Input should be a string representing the year (e.g. '2022').
    """
    logger.info(f"🟠 API Call: GET /api/v1/inflation/regional?year={year_str} 🟠")
    try:
        year = int(year_str.strip())
        if year not in [2020, 2021, 2022, 2023, 2024]:
            return json.dumps({
                "status": "error",
                "message": "Resource not found for specified year. Range must be 2020-2024."
            }, indent=2)
        
        data = {
            "year": year,
            "metric": "Southeast Asia Average Inflation (%)",
            "value": MOCK_API_CPI_REGIONAL["Southeast Asia Average Inflation"][year],
            "data_source": "ASEAN Statistical Portal (Mock API)",
            "api_status": "200 OK"
        }
        return json.dumps(data, indent=2)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Malformed request parameters: {str(e)}"
        }, indent=2)

def fetch_global_tech_index_api(year_str: str) -> str:
    """
    Simulates fetching the Global Tech Talent Index from an external API endpoint.
    Input should be a string representing the year (e.g., '2024').
    """
    logger.info(f"🟠 API Call: GET /api/v1/talent/tech-index?year={year_str} 🟠")
    try:
        year = int(year_str.strip())
        if year not in [2020, 2021, 2022, 2023, 2024]:
            return json.dumps({
                "status": "error",
                "message": "Data not found for year. Supported: 2020-2024."
            }, indent=2)
            
        data = {
            "year": year,
            "metric": "Global Tech Talent Demand Index (Base 100=2020)",
            "value": MOCK_API_CPI_REGIONAL["Global Tech Talent Index"][year],
            "data_source": "World Economic Forum Digital Economy Index (Mock API)",
            "api_status": "200 OK"
        }
        return json.dumps(data, indent=2)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Malformed request parameters: {str(e)}"
        }, indent=2)
