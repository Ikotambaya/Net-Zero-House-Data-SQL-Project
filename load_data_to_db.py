import sqlite3
import pandas as pd
import os # To handle file paths

# --- Configuration ---
DB_FILE = 'Net_zero_house_data.db'
CSV_FILE = 'Iko_Dissertation_Final_Dataset.csv'

# Get the directory where the script is located
script_dir = os.path.dirname(__file__)
# Construct full paths assuming files are in the same directory as the script
db_path = os.path.join(script_dir, DB_FILE)
csv_path = os.path.join(script_dir, CSV_FILE)

# --- Database Connection Function ---
def get_db_connection():
    """Establishes and returns a connection to the SQLite database."""
    conn = sqlite3.connect(db_path)
    # This allows us to access columns by name (e.g., row['ZoneName'])
    conn.row_factory = sqlite3.Row
    return conn

# --- Main Script Execution ---
if __name__ == '__main__':
    print(f"Attempting to connect to database: {db_path}")
    print(f"Attempting to read CSV file: {csv_path}")

    df = None # Initialize DataFrame outside try block
    try:
        # Load the CSV file into a Pandas DataFrame
        df = pd.read_csv(csv_path)
        print(f"CSV file '{CSV_FILE}' loaded successfully. Shape: {df.shape}")

        # Ensure 'Timestamp' column is in datetime format
        # This is crucial for proper storage and querying of dates/times
        df['Timestamp'] = pd.to_datetime(df['Timestamp'])

        # Convert Timestamp to string format suitable for SQLite DATETIME
        df['Timestamp'] = df['Timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')

    except FileNotFoundError:
        print(f"Error: CSV file '{CSV_FILE}' not found at {csv_path}")
        print("Please ensure the CSV file is in the same directory as this script.")
        exit() # Exit the script if the CSV isn't found
    except pd.errors.EmptyDataError:
        print(f"Error: The CSV file '{CSV_FILE}' is empty.")
        exit()
    except Exception as e:
        print(f"An error occurred while loading the CSV: {e}")
        import traceback
        traceback.print_exc()
        exit()

    conn = None # Initialize conn outside try block for finally
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # --- Populate Zones Table ---
        print("\nPopulating Zones table...")
        # Identify columns that represent zone-specific temperature data (e.g., 'Z1_temp')
        # Exclude 'Air_temperature' as it's a global/outdoor measurement
        zone_columns = [col for col in df.columns if '_temp' in col and col != 'Air_temperature']
        # Extract unique zone names (e.g., 'Z1', 'Z12+13') and sort them for consistency
        zone_names = sorted(list(set([col.split('_')[0] for col in zone_columns])))

        # Insert each unique zone name into the Zones table
        # INSERT OR IGNORE prevents inserting duplicates if the script is run multiple times
        for zone_name in zone_names:
            cursor.execute("INSERT OR IGNORE INTO Zones (ZoneName) VALUES (?)", (zone_name,))
        conn.commit() # Save changes to the database
        print(f"Zones inserted: {len(zone_names)}")

        # --- Populate Measurements Table ---
        print("\nPopulating Measurements table...")
        # Define all expected measurement names and their corresponding units.
        # Ensure these names exactly match how you expect to derive them from CSV column suffixes
        # or from the global outdoor columns.
        measurements_to_insert = {
            'temp': 'C',
            'RH': '%',
            'CO2': 'ppm',
            'valve_opening': '%',
            'window_opening': '%',
            'dew_point': 'C',
            'temp_diff': 'C',
            'RH_diff': '%',
            'Heat_Index': 'C',
            'CO2_AQI': 'AQI',
            'Condensation_Risk': 'Risk Level', # Example unit, adjust as needed
            'Comfortable_Humidity': 'Binary (0/1)', # Example unit, adjust as needed
            'Overheating_Risk': 'Risk Level', # Example unit, adjust as needed
            'Cooling': 'kW',
            'Heating': 'kW',
            'Air_temperature': 'C',
            'Relative_humidity': '%',
            'Wind_speed': 'm/s',
            'Rain': 'mm',
            'Solar_radiation': 'W/m^2',
            'Lighting': 'Lux', # Example unit, adjust as needed
            'outdoor_dew_point': 'C',
            'Outdoor_Heat_Index': 'C'
        }

        for name, unit in measurements_to_insert.items():
            cursor.execute("INSERT OR IGNORE INTO Measurements (MeasurementName, Unit) VALUES (?, ?)", (name, unit))
        conn.commit()
        print(f"Measurements inserted: {len(measurements_to_insert)}")

        # --- Retrieve Zone and Measurement IDs for efficient lookup ---
        # Query the database to get mapping dictionaries (name -> ID)
        # This avoids repeated database queries during the main data insertion loop
        print("\nFetching Zone and Measurement IDs for lookup...")
        zone_id_map = {row['ZoneName']: row['ZoneID'] for row in cursor.execute("SELECT ZoneID, ZoneName FROM Zones").fetchall()}
        measurement_id_map = {row['MeasurementName']: row['MeasurementID'] for row in cursor.execute("SELECT MeasurementID, MeasurementName FROM Measurements").fetchall()}
        print("Lookup maps created.")

        # --- Populate HourlyOutdoorReadings Table ---
        print("\nPopulating HourlyOutdoorReadings table...")
        # Define the columns that belong to the HourlyOutdoorReadings table
        outdoor_cols = [
            'Timestamp', 'Cooling', 'Heating', 'Air_temperature', 'Relative_humidity',
            'Wind_speed', 'Rain', 'Solar_radiation', 'Lighting', 'outdoor_dew_point', 'Outdoor_Heat_Index'
        ]
        # Select only these columns from the main DataFrame
        df_outdoor = df[outdoor_cols].copy()

        # Convert DataFrame rows to a list of tuples for efficient bulk insertion
        outdoor_data = [tuple(row) for row in df_outdoor.values]

        outdoor_insert_sql = """
        INSERT INTO HourlyOutdoorReadings (
            Timestamp, Cooling, Heating, Air_temperature, Relative_humidity,
            Wind_speed, Rain, Solar_radiation, Lighting, Outdoor_dew_point, Outdoor_Heat_Index
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        # Use executemany for bulk insertion, which is much faster than individual inserts
        cursor.executemany(outdoor_insert_sql, outdoor_data)
        conn.commit()
        print(f"Inserted {len(outdoor_data)} rows into HourlyOutdoorReadings.")

        # --- Populate HourlyZoneReadings Table (The Unpivoting Process) ---
        print("\nPopulating HourlyZoneReadings table...")

        zone_reading_data = [] # This list will hold all the transformed rows
        # Iterate through each row (each hourly record) of the original DataFrame
        for index, row in df.iterrows():
            timestamp = row['Timestamp']

            # Iterate through each defined zone
            for zone_name in zone_names:
                zone_id = zone_id_map.get(zone_name)
                if zone_id is None:
                    # This should ideally not happen if zone_names are correctly extracted
                    print(f"Warning: Zone '{zone_name}' not found in Zones table. Skipping data for this zone.")
                    continue

                # Iterate through each measurement type
                for measurement_name, measurement_id in measurement_id_map.items():
                    # Skip measurements that are designed for the HourlyOutdoorReadings table
                    if measurement_name in [
                        'Cooling', 'Heating', 'Air_temperature', 'Relative_humidity',
                        'Wind_speed', 'Rain', 'Solar_radiation', 'Lighting',
                        'outdoor_dew_point', 'Outdoor_Heat_Index'
                    ]:
                        continue # These are global, not zone-specific

                    # Construct the original column name as it appears in the CSV
                    # e.g., 'Z1_temp', 'Z12+13_valve_opening'
                    csv_col_name = f"{zone_name}_{measurement_name}"

                    # Check if this specific column exists in the DataFrame
                    # (Some combinations might not exist if data is sparse or irregular)
                    if csv_col_name in df.columns:
                        value = row[csv_col_name]
                        # Convert Pandas' NaN (Not a Number) to Python's None,
                        # which SQLite stores as NULL
                        if pd.isna(value):
                            value = None

                        # Add the transformed row data to our list
                        zone_reading_data.append((timestamp, zone_id, measurement_id, value))
                    # else:
                        # Uncomment this if you want to see warnings for missing columns
                        # print(f"Warning: Column '{csv_col_name}' not found in CSV. Skipping for zone '{zone_name}', measurement '{measurement_name}'.")

        zone_readings_insert_sql = """
        INSERT INTO HourlyZoneReadings (Timestamp, ZoneID, MeasurementID, Value)
        VALUES (?, ?, ?, ?)
        """
        # Insert all collected zone readings in a single bulk operation
        cursor.executemany(zone_readings_insert_sql, zone_reading_data)
        conn.commit()
        print(f"Inserted {len(zone_reading_data)} rows into HourlyZoneReadings.")

    except sqlite3.Error as e:
        print(f"Database error during data population: {e}")
        import traceback
        traceback.print_exc() # Print full traceback for database errors
    except Exception as e: # Catch any other unexpected errors during processing
        print(f"An unexpected error occurred during data processing: {e}")
        import traceback
        traceback.print_exc() # Print full traceback for unexpected errors
    finally:
        # Ensure the database connection is always closed, even if errors occur
        if conn:
            conn.close()
            print("Database connection closed.")