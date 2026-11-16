import psycopg2
from psycopg2.extras import RealDictCursor
from app.config import Config


class DatabaseError(Exception):
    pass


class Database:
    def __init__(self):
        self.conn_params = {
            "host": Config.DB_HOST,
            "port": Config.DB_PORT,
            "dbname": Config.DB_NAME,
            "user": Config.DB_USER,
            "password": Config.DB_PASSWORD
        }

    def get_connection(self):
        try:
            return psycopg2.connect(**self.conn_params)
        except psycopg2.Error as e:
            raise DatabaseError(f"Не вдалося підключитися до БД PostgreSQL: {e}")

    def init_db(self):
        create_cities_sql = """
        CREATE TABLE IF NOT EXISTS cities (
            id INTEGER PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            country VARCHAR(10) NOT NULL,
            population INTEGER DEFAULT 0,
            timezone INTEGER DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """

        create_forecasts_sql = """
        CREATE TABLE IF NOT EXISTS forecasts (
            id SERIAL PRIMARY KEY,
            city_id INTEGER NOT NULL REFERENCES cities(id) ON DELETE CASCADE,
            forecast_time TIMESTAMP NOT NULL,
            temp NUMERIC(5, 2) NOT NULL,
            feels_like NUMERIC(5, 2) NOT NULL,
            humidity INTEGER NOT NULL,
            description VARCHAR(255) NOT NULL,
            wind_speed NUMERIC(5, 2) NOT NULL,
            CONSTRAINT unique_city_forecast UNIQUE (city_id, forecast_time)
        );
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(create_cities_sql)
                cur.execute(create_forecasts_sql)
            conn.commit()

    def save_weather_data(self, parsed_data: dict):
        city = parsed_data["city"]
        forecasts = parsed_data["forecasts"]

        upsert_city_sql = """
        INSERT INTO cities (id, name, country, population, timezone, updated_at)
        VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (id) DO UPDATE SET
            name = EXCLUDED.name,
            country = EXCLUDED.country,
            population = EXCLUDED.population,
            timezone = EXCLUDED.timezone,
            updated_at = CURRENT_TIMESTAMP;
        """

        upsert_forecast_sql = """
        INSERT INTO forecasts (city_id, forecast_time, temp, feels_like, humidity, description, wind_speed)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (city_id, forecast_time) DO UPDATE SET
            temp = EXCLUDED.temp,
            feels_like = EXCLUDED.feels_like,
            humidity = EXCLUDED.humidity,
            description = EXCLUDED.description,
            wind_speed = EXCLUDED.wind_speed;
        """

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(upsert_city_sql, (
                        city["city_id"],
                        city["name"],
                        city["country"],
                        city["population"],
                        city["timezone"]
                    ))

                    for f in forecasts:
                        cur.execute(upsert_forecast_sql, (
                            city["city_id"],
                            f["dt_txt"],
                            f["temp"],
                            f["feels_like"],
                            f["humidity"],
                            f["description"],
                            f["wind_speed"]
                        ))
                conn.commit()
        except psycopg2.Error as e:
            raise DatabaseError(f"Помилка збереження даних у БД: {e}")

    def get_all_cities(self) -> list:
        sql = "SELECT id, name, country, population, updated_at FROM cities ORDER BY updated_at DESC;"
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(sql)
                    return cur.fetchall()
        except psycopg2.Error as e:
            raise DatabaseError(f"Помилка читання міст із БД: {e}")

    def get_forecasts_by_city(self, city_id: int) -> list:
        sql = """
        SELECT 
            c.name AS city_name,
            c.country,
            f.forecast_time,
            f.temp,
            f.feels_like,
            f.humidity,
            f.description,
            f.wind_speed
        FROM forecasts f
        JOIN cities c ON f.city_id = c.id
        WHERE c.id = %s
        ORDER BY f.forecast_time ASC;
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(sql, (city_id,))
                    return cur.fetchall()
        except psycopg2.Error as e:
            raise DatabaseError(f"Помилка читання прогнозів із БД: {e}")
