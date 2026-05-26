from sqlalchemy.orm import Session
from backend.app.database import engine, Base, SessionLocal
from backend.app.models import MOMEmployment, SingStatPopulation, SingStatCPI

def seed_database(db: Session):
    # Create all tables first
    Base.metadata.create_all(bind=engine)

    # 1. Check if we already have data
    if db.query(MOMEmployment).first() is not None:
        print("Database already seeded. Skipping...")
        return

    print("Seeding database with Singapore government mock statistics (2020-2024)...")

    # 2. Seed MOM Employment Data
    mom_data = [
        # Technology Sector
        MOMEmployment(year=2020, sector="Technology", employment_change=8500, unemployment_rate=2.8, median_salary=6500),
        MOMEmployment(year=2021, sector="Technology", employment_change=12000, unemployment_rate=2.1, median_salary=7000),
        MOMEmployment(year=2022, sector="Technology", employment_change=15000, unemployment_rate=1.8, median_salary=7600),
        MOMEmployment(year=2023, sector="Technology", employment_change=3200, unemployment_rate=3.1, median_salary=7900),  # Tech layoffs period
        MOMEmployment(year=2024, sector="Technology", employment_change=6800, unemployment_rate=2.4, median_salary=8200),

        # Financial Services Sector
        MOMEmployment(year=2020, sector="Financial Services", employment_change=3500, unemployment_rate=2.2, median_salary=7200),
        MOMEmployment(year=2021, sector="Financial Services", employment_change=5200, unemployment_rate=1.9, median_salary=7500),
        MOMEmployment(year=2022, sector="Financial Services", employment_change=6100, unemployment_rate=1.7, median_salary=8000),
        MOMEmployment(year=2023, sector="Financial Services", employment_change=4800, unemployment_rate=2.0, median_salary=8300),
        MOMEmployment(year=2024, sector="Financial Services", employment_change=5500, unemployment_rate=1.9, median_salary=8600),

        # Healthcare Sector
        MOMEmployment(year=2020, sector="Healthcare", employment_change=4500, unemployment_rate=1.2, median_salary=4800),
        MOMEmployment(year=2021, sector="Healthcare", employment_change=6200, unemployment_rate=1.1, median_salary=5100),
        MOMEmployment(year=2022, sector="Healthcare", employment_change=5800, unemployment_rate=1.3, median_salary=5300),
        MOMEmployment(year=2023, sector="Healthcare", employment_change=6400, unemployment_rate=1.2, median_salary=5500),
        MOMEmployment(year=2024, sector="Healthcare", employment_change=7000, unemployment_rate=1.1, median_salary=5800),

        # Tourism & Hospitality (COVID impact & recovery)
        MOMEmployment(year=2020, sector="Tourism & Hospitality", employment_change=-18000, unemployment_rate=6.5, median_salary=2800),
        MOMEmployment(year=2021, sector="Tourism & Hospitality", employment_change=-5000, unemployment_rate=5.2, median_salary=2900),
        MOMEmployment(year=2022, sector="Tourism & Hospitality", employment_change=12000, unemployment_rate=3.5, median_salary=3200),
        MOMEmployment(year=2023, sector="Tourism & Hospitality", employment_change=14500, unemployment_rate=2.8, median_salary=3400),
        MOMEmployment(year=2024, sector="Tourism & Hospitality", employment_change=8000, unemployment_rate=2.5, median_salary=3600),
    ]
    db.add_all(mom_data)

    # 3. Seed SingStat Population Data
    pop_data = [
        SingStatPopulation(year=2020, resident_population=5685800, median_age=41.5, dependency_ratio=18.6),
        SingStatPopulation(year=2021, resident_population=5453600, median_age=41.8, dependency_ratio=19.2),  # Pandemc drop
        SingStatPopulation(year=2022, resident_population=5637000, median_age=42.1, dependency_ratio=19.9),
        SingStatPopulation(year=2023, resident_population=5917600, median_age=42.5, dependency_ratio=20.8),
        SingStatPopulation(year=2024, resident_population=6050000, median_age=42.8, dependency_ratio=21.5),
    ]
    db.add_all(pop_data)

    # 4. Seed SingStat CPI (Inflation) Data (monthly for categories: All Items, Housing, Food, Transport)
    cpi_categories = ["All Items", "Food", "Housing", "Transport"]
    cpi_base_values = {
        "All Items": {2020: 99.1, 2021: 101.4, 2022: 107.6, 2023: 112.8, 2024: 115.5},  # CPI spike in 2022-2023
        "Food": {2020: 98.8, 2021: 100.2, 2022: 105.5, 2023: 111.6, 2024: 114.2},
        "Housing": {2020: 99.5, 2021: 100.9, 2022: 106.1, 2023: 110.8, 2024: 113.1},
        "Transport": {2020: 97.2, 2021: 104.5, 2022: 117.8, 2023: 124.2, 2024: 126.9},
    }
    
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    cpi_records = []
    
    for category in cpi_categories:
        for year in range(2020, 2025):
            base = cpi_base_values[category][year]
            for i, month in enumerate(months):
                # Add minor monthly fluctuation around base
                fluctuation = (i - 5.5) * 0.15
                cpi_val = round(base + fluctuation, 2)
                cpi_records.append(
                    SingStatCPI(year=year, month=month, cpi_index=cpi_val, category=category)
                )

    db.add_all(cpi_records)
    db.commit()
    print("Database seeding completed successfully!")

if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
