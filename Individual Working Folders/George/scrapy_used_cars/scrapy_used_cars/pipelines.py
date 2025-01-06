import psycopg2
from datetime import datetime


class UsedCarsPipeline:
    def open_spider(self, spider):
        # Connect to PostgreSQL when the spider opens
        self.connection = psycopg2.connect(
            dbname="lookers",
            user="postgres",
            password="postgres",
            host="localhost",
        )
        self.cursor = self.connection.cursor()

        # Create the cargiant table if it doesn't exist
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS car_db (
                id SERIAL PRIMARY KEY,
                make VARCHAR(100),
                model VARCHAR(100),
                price NUMERIC,
                mileage NUMERIC,
                fuel_type VARCHAR(50),
                body_style VARCHAR(100),
                engine_size NUMERIC,
                hp INT,
                transmission VARCHAR(50),
                year INT,
                dealership_name VARCHAR(255),
                mpg VARCHAR(50),
                n_doors INT,
                previous_owners INT,
                droplet VARCHAR(50),
                feature_list TEXT,
                last_updated TIMESTAMP
            );
            """
        )
        self.connection.commit()

    def close_spider(self, spider):
        # Close the database connection
        self.cursor.close()
        self.connection.close()

    def process_item(self, item, spider):
        # Insert or update the car listing
        try:
            self.cursor.execute(
                """
                INSERT INTO car_db (
                    make, model, price, mileage, fuel_type, body_style, engine_size, hp,
                    transmission, year, dealership_name, mpg, n_doors, previous_owners,
                    droplet, feature_list, last_updated
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    make = EXCLUDED.make,
                    model = EXCLUDED.model,
                    price = EXCLUDED.price,
                    mileage = EXCLUDED.mileage,
                    fuel_type = EXCLUDED.fuel_type,
                    body_style = EXCLUDED.body_style,
                    engine_size = EXCLUDED.engine_size,
                    hp = EXCLUDED.hp,
                    transmission = EXCLUDED.transmission,
                    year = EXCLUDED.year,
                    dealership_name = EXCLUDED.dealership_name,
                    mpg = EXCLUDED.mpg,
                    n_doors = EXCLUDED.n_doors,
                    previous_owners = EXCLUDED.previous_owners,
                    droplet = EXCLUDED.droplet,
                    feature_list = EXCLUDED.feature_list,
                    last_updated = EXCLUDED.last_updated;
                """,
                (
                    item.get("make"),
                    item.get("model"),
                    float(item.get("price")) if item.get("price") else None,
                    float(item.get("mileage")) if item.get("mileage") else None,
                    item.get("fuel_type"),
                    item.get("body_style"),
                    item.get("engine_size"),
                    item.get("hp"),
                    item.get("transmission"),
                    int(item.get("year")) if item.get("year") else None,
                    item.get("dealership_name"), 
                    item.get("mpg"), 
                    item.get("n_doors"), 
                    item.get("previous_owners"), 
                    item.get("droplet"), 
                    item.get("feature_list"),  
                    datetime.now(),
                ),
            )
            self.connection.commit()
        except Exception as e:
            spider.logger.error(f"Database insertion error: {e}")
            self.connection.rollback()
        return item
