🏠 Net-Zero House Data Analysis (SQL & Python)

Overview
This project showcases practical competencies in relational database design, data transformation (ETL), and SQL querying using a rich, real-world dataset. It focuses on analysing two years of hourly sensor data from a net-zero energy house, encompassing 15 internal zones and concurrent outdoor environmental conditions.

The core objective was to convert a wide, flat CSV file into a normalised relational database to facilitate efficient data storage, advanced querying, and foundational insights into building performance and comfort.

📁 Dataset
File: Iko_Dissertation_Final_Dataset.csv
Contents: ~17,500 hourly records × 206 columns
Each row corresponds to a unique hour. Columns capture a wide range of variables, including:

Indoor (per zone): Temperature, relative humidity, CO₂ levels, dew point, heat index, condensation risk, comfort index, valve/window status

Outdoor: Air temperature, relative humidity, wind speed, rainfall, solar radiation, lighting, dew point, heat index

🧱 Database Design
A normalised schema was employed to reduce redundancy, improve consistency, and support powerful, flexible queries. The schema consists of four interrelated tables:

1. Zones
Stores metadata for each monitored zone.

Column	Description
ZoneID	Primary key
ZoneName	Name of the zone

2. Measurements
Defines all types of sensor measurements.

Column	Description
MeasurementID	Primary key
MeasurementName	Type (e.g., temp, CO₂)
Unit	Unit of measurement

3. HourlyOutdoorReadings
Captures hourly environmental conditions outside the house.

Column	Description
OutdoorReadingID	Primary key
Timestamp	ISO-formatted datetime
Various metrics	Air temp, humidity, wind, etc.

4. HourlyZoneReadings
Holds the core time-series data for all zones and measurement types, in a long format.

Column	Description
ReadingID	Primary key
Timestamp	Hour of recording
ZoneID	FK → Zones
MeasurementID	FK → Measurements
Value	Recorded value (NULL if missing)

Key Relationships:

HourlyZoneReadings.ZoneID → Zones.ZoneID

HourlyZoneReadings.MeasurementID → Measurements.MeasurementID

🛠 Tools & Technologies
SQLite: Lightweight database engine for schema and queries

Python: For ETL scripting

pandas: Data parsing and manipulation

sqlite3: Python interface for SQLite

DB Browser for SQLite: GUI for inspecting and querying the DB

Git & GitHub: Version control and portfolio hosting

🔄 ETL Script: load_data_to_db.py
This script handles the full extract–transform–load process:

Key Steps:
Database Connection
Connects to Net_zero_house_data.db.

CSV Ingestion
Loads the CSV into a pandas DataFrame. The Timestamp is parsed into ISO format.

Static Table Population

Extracts all unique zone names to populate Zones.

Defines sensor types and units for Measurements.

Outdoor Data Loading
Outdoor metrics are inserted into HourlyOutdoorReadings via executemany for efficiency.

Zone Data Transformation

The CSV’s wide format is unpivoted.

Each zone-measurement combination is mapped dynamically.

Missing values (NaNs) are stored as SQL NULL.

📊 Example SQL Queries
1. List All Zones
sql
Copy
Edit
SELECT ZoneID, ZoneName FROM Zones;
2. List All Measurement Types
sql
Copy
Edit
SELECT MeasurementName, Unit FROM Measurements;
3. Retrieve Outdoor Air Temperature & Humidity (First 10 Rows)
sql
Copy
Edit
SELECT Timestamp, Air_temperature, Relative_humidity
FROM HourlyOutdoorReadings
ORDER BY Timestamp
LIMIT 10;
4. Get Temperature for Zone 'Z1' on 1st Jan 2023
sql
Copy
Edit
SELECT HZR.Timestamp, HZR.Value AS TemperatureC
FROM HourlyZoneReadings HZR
JOIN Zones Z ON HZR.ZoneID = Z.ZoneID
JOIN Measurements M ON HZR.MeasurementID = M.MeasurementID
WHERE Z.ZoneName = 'Z1' AND M.MeasurementName = 'temp'
  AND STRFTIME('%Y-%m-%d', HZR.Timestamp) = '2023-01-01'
ORDER BY HZR.Timestamp;
5. Daily Average CO₂ Level per Zone
sql
Copy
Edit
SELECT STRFTIME('%Y-%m-%d', HZR.Timestamp) AS ReadingDate,
       Z.ZoneName,
       AVG(HZR.Value) AS AverageCO2_ppm
FROM HourlyZoneReadings HZR
JOIN Zones Z ON HZR.ZoneID = Z.ZoneID
JOIN Measurements M ON HZR.MeasurementID = M.MeasurementID
WHERE M.MeasurementName = 'CO2'
GROUP BY ReadingDate, Z.ZoneName
ORDER BY ReadingDate, Z.ZoneName;
6. Compare Indoor (Zone Z1) vs Outdoor Temperature
sql
Copy
Edit
SELECT HO.Timestamp,
       HO.Air_temperature AS OutdoorTemperatureC,
       HZR.Value AS Z1_TemperatureC
FROM HourlyOutdoorReadings HO
JOIN HourlyZoneReadings HZR ON HO.Timestamp = HZR.Timestamp
JOIN Zones Z ON HZR.ZoneID = Z.ZoneID
JOIN Measurements M ON HZR.MeasurementID = M.MeasurementID
WHERE Z.ZoneName = 'Z1' AND M.MeasurementName = 'temp'
ORDER BY HO.Timestamp
LIMIT 24;
🚀 Getting Started
To run this project locally:

Clone the repository

bash
Copy
Edit
git clone https://github.com/your-username/Net-Zero-House-Data-SQL-Project.git
cd Net-Zero-House-Data-SQL-Project
Add Dataset
Place Iko_Dissertation_Final_Dataset.csv into the project root.

Set up Python Environment
Ensure Python and pandas are installed (use Anaconda if unsure).

Run the ETL Script

bash
Copy
Edit
python load_data_to_db.py
This will create and populate Net_zero_house_data.db.

Explore the Database
Open the database in DB Browser for SQLite and start querying.

🔍 Future Enhancements
📈 Advanced Analysis
Time-based aggregation (daily, weekly, seasonal)

Correlation analysis between indoor metrics and weather

Energy usage pattern detection

Condensation and overheating risk analysis

📊 Visualisation
Use tools like Matplotlib, Seaborn, or Plotly to:

Visualise trends and anomalies

Build interactive dashboards

🤖 Machine Learning
Predict temperature/humidity levels

Model comfort risk

Forecast window/valve actuation

⚙️ Optimisation
Add indices for performance tuning on large-scale queries

📌 Summary
This project highlights how real-world sensor data can be structured, queried, and analysed using industry-standard tools. The normalised design not only simplifies querying but also sets a solid foundation for more complex analysis, visualisation, and machine learning applications.