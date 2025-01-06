# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

class UsedCarsLookerPipeline:
    
    def __init__(self):
        hostname = 'localhost'
        username = 'postgres'
        password = 'C1k3nR@!s'
        database = 'lookers'
        
        # Connect to PostgreSQL server to check or create the database
        server_connection = psycopg2.connect(host=hostname, user=username, password=password)
        server_connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)  # Allow database creation without explicit commit 
        server_cursor = server_connection.cursor() # used to execute sql commands in the server

        # Check if the database exists
        server_cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{database}'")
        if not server_cursor.fetchone():
            server_cursor.execute(f"CREATE DATABASE {database}")  # Create the database if it doesn't exist
            print(f"Database '{database}' created.")
        server_cursor.close()
        server_connection.close()

        ## Create/Connect to database
        self.connection = psycopg2.connect(host=hostname, user=username, password=password, dbname=database)
        
        ## Create cursor, used to execute commands
        self.cur = self.connection.cursor()
        
        ## Create quotes table if none exists
        self.cur.execute("""
        CREATE TABLE IF NOT EXISTS lookers (
            id SERIAL PRIMARY KEY,
            make VARCHAR(100),
            model VARCHAR(100),
            price NUMERIC,
            mileage NUMERIC,
            fuel_type VARCHAR(50),
            body_style VARCHAR(100),
            engine_size VARCHAR(50),
            transmission VARCHAR(50),
            year INT,
            dealership_name VARCHAR(255),
            mpg VARCHAR(50),
            n_doors VARCHAR(50),
            previous_owners VARCHAR(50),
            droplet VARCHAR(50),
            feature_list TEXT
        )
        """)
        # deelte the registered_date
    
    def process_item(self, item, spider):
        # Insert the scraped item into the PostgreSQL table
        self.cur.execute("""
            INSERT INTO lookers (
                make, model, price, mileage, fuel_type, body_style, 
                engine_size, transmission, year, dealership_name, 
                mpg, n_doors, previous_owners, droplet, feature_list
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            item.get('make'),
            item.get('model'),
            item.get('price'),
            item.get('mileage'),
            item.get('fuel_type'),
            item.get('body_style'),
            item.get('engine_size'),
            item.get('transmission'),
            item.get('year'),
            item.get('dealership_name'),
            item.get('mpg'),
            item.get('n_doors'),
            item.get('previous_owners'),
            item.get('droplet'),
            ', '.join(item.get('feature_list', []))  # convert list to comma-separated string
        ))
        self.connection.commit()
        
        return item
    
    
    def close_spider(self, spider):
        self.cur.close()
        self.connection.close()
