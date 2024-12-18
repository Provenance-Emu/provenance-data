#!/usr/bin/env python3
import json
import sqlite3
from pathlib import Path

def create_database(db_path: str):
    """Create SQLite database with proper schema"""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Create tables based on the schema we found
    c.executescript("""
        -- Platforms/Systems table
        CREATE TABLE IF NOT EXISTS systems (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            alias TEXT
        );

        -- Main games table
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY,
            game_title TEXT NOT NULL,
            release_date TEXT,
            platform INTEGER,
            region_id INTEGER,
            country_id INTEGER,
            overview TEXT,
            youtube TEXT,
            players INTEGER,
            coop TEXT,
            rating TEXT,
            FOREIGN KEY (platform) REFERENCES systems(id)
        );

        -- Many-to-many relationship tables
        CREATE TABLE IF NOT EXISTS game_developers (
            game_id INTEGER,
            developer_id INTEGER,
            PRIMARY KEY (game_id, developer_id),
            FOREIGN KEY (game_id) REFERENCES games(id)
        );

        CREATE TABLE IF NOT EXISTS game_genres (
            game_id INTEGER,
            genre_id INTEGER,
            PRIMARY KEY (game_id, genre_id),
            FOREIGN KEY (game_id) REFERENCES games(id)
        );

        CREATE TABLE IF NOT EXISTS game_publishers (
            game_id INTEGER,
            publisher_id INTEGER,
            PRIMARY KEY (game_id, publisher_id),
            FOREIGN KEY (game_id) REFERENCES games(id)
        );

        -- Alternate titles
        CREATE TABLE IF NOT EXISTS game_alternates (
            game_id INTEGER,
            alternate_title TEXT,
            PRIMARY KEY (game_id, alternate_title),
            FOREIGN KEY (game_id) REFERENCES games(id)
        );

        -- Artwork table
        CREATE TABLE IF NOT EXISTS game_artwork (
            id INTEGER PRIMARY KEY,
            game_id INTEGER,
            type TEXT,
            side TEXT,
            filename TEXT,
            resolution TEXT,
            FOREIGN KEY (game_id) REFERENCES games(id)
        );

        -- Create indexes for better search performance
        CREATE INDEX IF NOT EXISTS idx_games_title ON games(game_title);
        CREATE INDEX IF NOT EXISTS idx_games_platform ON games(platform);
        CREATE INDEX IF NOT EXISTS idx_systems_name ON systems(name);
    """)

    conn.commit()
    return conn

def safe_insert_many(cursor, sql, data):
    """Insert many records, skipping duplicates"""
    for item in data:
        try:
            cursor.execute(sql, item)
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                continue  # Skip duplicates
            else:
                raise  # Re-raise other integrity errors

def import_data(conn: sqlite3.Connection, json_path: str):
    """Import data from JSON file into SQLite database"""
    with open(json_path) as f:
        data = json.load(f)

    c = conn.cursor()

    # Import platforms/systems first
    if 'include' in data and 'platform' in data['include']:
        print("Importing platforms...")
        platforms = data['include']['platform']['data']
        for platform_id, platform_data in platforms.items():
            try:
                c.execute("""
                    INSERT OR REPLACE INTO systems (id, name, alias)
                    VALUES (?, ?, ?)
                """, (
                    platform_data['id'],
                    platform_data['name'],
                    platform_data.get('alias')
                ))
            except Exception as e:
                print(f"Error importing platform {platform_id}: {e}")

        print(f"Imported {len(platforms)} platforms")
        conn.commit()

    total_games = len(data['data']['games'])
    print(f"Found {total_games} games to import")

    # Use a transaction for better performance
    with conn:
        for i, game in enumerate(data['data']['games'], 1):
            if i % 1000 == 0:
                print(f"Processing game {i}/{total_games}...")

            try:
                # Insert main game data
                c.execute("""
                    INSERT OR REPLACE INTO games (
                        id, game_title, release_date, platform, region_id,
                        country_id, overview, youtube, players, coop, rating
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    game['id'], game['game_title'], game.get('release_date'),
                    game.get('platform'), game.get('region_id'), game.get('country_id'),
                    game.get('overview'), game.get('youtube'), game.get('players'),
                    game.get('coop'), game.get('rating')
                ))

                # Insert developers
                if game.get('developers'):
                    safe_insert_many(
                        c,
                        "INSERT OR IGNORE INTO game_developers (game_id, developer_id) VALUES (?, ?)",
                        [(game['id'], dev_id) for dev_id in game['developers']]
                    )

                # Insert genres
                if game.get('genres'):
                    safe_insert_many(
                        c,
                        "INSERT OR IGNORE INTO game_genres (game_id, genre_id) VALUES (?, ?)",
                        [(game['id'], genre_id) for genre_id in game['genres']]
                    )

                # Insert publishers
                if game.get('publishers'):
                    safe_insert_many(
                        c,
                        "INSERT OR IGNORE INTO game_publishers (game_id, publisher_id) VALUES (?, ?)",
                        [(game['id'], pub_id) for pub_id in game['publishers']]
                    )

                # Insert alternates
                if game.get('alternates'):
                    # Filter out None/null values and ensure uniqueness
                    alternates = list(set(alt for alt in game['alternates'] if alt))
                    safe_insert_many(
                        c,
                        "INSERT OR IGNORE INTO game_alternates (game_id, alternate_title) VALUES (?, ?)",
                        [(game['id'], alt) for alt in alternates]
                    )

            except Exception as e:
                print(f"Error processing game {game['id']} ({game['game_title']}): {e}")

        # Import artwork if available
        if 'include' in data and 'boxart' in data['include']:
            print("Importing artwork...")
            artwork_count = 0

            for game_id, artworks in data['include']['boxart']['data'].items():
                for art in artworks:
                    try:
                        c.execute("""
                            INSERT OR REPLACE INTO game_artwork (game_id, type, side, filename, resolution)
                            VALUES (?, ?, ?, ?, ?)
                        """, (
                            int(game_id), art['type'], art.get('side'),
                            art['filename'], art.get('resolution')
                        ))
                        artwork_count += 1
                    except Exception as e:
                        print(f"Error importing artwork for game {game_id}: {e}")

            print(f"Imported {artwork_count} artwork entries")

def main():
    json_path = 'database-latest.json'
    db_path = 'games.db'

    print(f"Creating database at {db_path}...")
    conn = create_database(db_path)

    print(f"Importing data from {json_path}...")
    import_data(conn, json_path)

    # Print some stats
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM games")
    games_count = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM game_artwork")
    artwork_count = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM systems")
    systems_count = c.fetchone()[0]

    print(f"\nDatabase Statistics:")
    print(f"Total Systems: {systems_count}")
    print(f"Total Games: {games_count}")
    print(f"Total Artwork: {artwork_count}")

    conn.close()
    print("Done!")

if __name__ == "__main__":
    main()
