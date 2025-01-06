import tkinter as tk
from tkinter import ttk
import psycopg2
from decimal import Decimal

# Database connection parameters
DB_NAME = "lookers"
DB_USER = "postgres"
DB_PASS = "postgres"
DB_HOST = "localhost"


class CarFilterApp:
    def __init__(self, master):
        self.master = master
        master.title("Car Search")

        # Frame for filters (left side)
        self.filter_frame = tk.Frame(master, padx=10, pady=10)
        self.filter_frame.grid(row=0, column=0, sticky="n")

        # Frame for results (right side)
        self.result_frame = tk.Frame(master, padx=10, pady=10)
        self.result_frame.grid(row=0, column=1, sticky="n")

        # Fields to filter on
        self.fields = {
            "make": "text",
            "model": "text",
            "fuel_type": "text",
            "body_style": "text",
            "transmission": "text",
            "price": "numeric",
            "mileage": "numeric",
            "year": "numeric",
            "n_doors": "numeric",
            "previous_owners": "numeric",
            "engine_size": "numeric",
            "hp": "numeric"
        }

        self.entries = {}
        row_count = 0
        for field_name, field_type in self.fields.items():
            label = tk.Label(self.filter_frame, text=f"{field_name.capitalize()}:")
            label.grid(row=row_count, column=0, sticky="e", pady=2)
            entry = tk.Entry(self.filter_frame, width=20)
            entry.grid(row=row_count, column=1, pady=2)
            self.entries[field_name] = entry
            row_count += 1

        # Add a search button
        self.search_button = tk.Button(self.filter_frame, text="Search", command=self.run_search)
        self.search_button.grid(row=row_count, column=0, columnspan=2, pady=10)

        # Results table (top right)
        self.table_label = tk.Label(self.result_frame, text="Top 5 Matches", font=("Arial", 14, "bold"))
        self.table_label.grid(row=0, column=0, sticky="w")

        # Define Treeview columns dynamically
        self.tree_columns = list(self.fields.keys())
        self.tree = ttk.Treeview(self.result_frame, columns=self.tree_columns, show='headings')

        for column in self.tree_columns:
            self.tree.heading(column, text=column.capitalize())
            self.tree.column(column, width=100)

        self.tree.grid(row=1, column=0, sticky="nsew")

        # Average price label (bottom right)
        self.avg_label = tk.Label(self.result_frame, text="Average Price: N/A")
        self.avg_label.grid(row=2, column=0, sticky="w", pady=10)

        # Make the columns stretch
        self.result_frame.grid_rowconfigure(1, weight=1)
        self.result_frame.grid_columnconfigure(0, weight=1)

    def run_search(self):
        # Collect user inputs
        user_inputs = {f: self.entries[f].get().strip() for f in self.fields}
        
        # Prepare filters
        filters = []
        values = []

        try:
            conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
            cur = conn.cursor()

            for field_name, field_type in self.fields.items():
                val = user_inputs[field_name]
                if val:
                    if field_type == "text":
                        # exact match, case-insensitive
                        filters.append(f"LOWER({field_name}) = LOWER(%s)")
                        values.append(val)
                    else:
                        # numeric: use standard deviation from the database for that field
                        try:
                            num_val = float(val)
                            # Get standard deviation for this field from the entire dataset
                            std_query = f"SELECT stddev_samp({field_name}) FROM car_db;"
                            cur.execute(std_query)
                            std_dev = cur.fetchone()[0]

                            if std_dev is not None:
                                std_dev = float(std_dev)  # Convert Decimal to float
                            else:
                                std_dev = 0  # Fallback if no stddev available

                            low = num_val - std_dev
                            high = num_val + std_dev
                            filters.append(f"{field_name} BETWEEN %s AND %s")
                            values.extend([low, high])

                        except ValueError:
                            pass  # Invalid numeric input, skip

            where_clause = ""
            if filters:
                where_clause = "WHERE " + " AND ".join(filters)

            # Query for top 5 matches
            query = f"""
                SELECT {', '.join(self.fields.keys())}
                FROM car_db
                {where_clause}
                ORDER BY price ASC
                LIMIT 5;
            """

            # Query for average price
            avg_query = f"""
                SELECT AVG(price), COUNT(*)
                FROM car_db
                {where_clause};
            """

            cur.execute(query, tuple(values))
            rows = cur.fetchall()

            # Clear existing rows in Treeview
            for i in self.tree.get_children():
                self.tree.delete(i)

            # Insert new rows
            for r in rows:
                self.tree.insert("", tk.END, values=r)

            # Compute average price
            cur.execute(avg_query, tuple(values))
            avg_res = cur.fetchone()
            avg_price, count = avg_res[0], avg_res[1]

            if avg_price is not None:
                self.avg_label.config(text=f"Average Price: {round(avg_price, 2)} (based on {count} cars)")
            else:
                self.avg_label.config(text="Average Price: N/A (no matches)")

            conn.close()

        except Exception as e:
            print(f"Database error: {e}")
            self.avg_label.config(text="Error fetching data.")


if __name__ == "__main__":
    root = tk.Tk()
    app = CarFilterApp(root)
    root.mainloop()
