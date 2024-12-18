import argparse
import json
import sqlite3
import os
from pathlib import Path
import requests
from tqdm import tqdm
import time
from difflib import get_close_matches
import concurrent.futures
from functools import partial
import re

GAMESDB_CDN = "https://cdn.thegamesdb.net/"

class ROMDownloader:
    def __init__(self, artwork_only=False):
        self.artwork_only = artwork_only
        self.db_conn = sqlite3.connect('games.db')
        self.db_conn.row_factory = sqlite3.Row

        # Load assets.cores.json
        try:
            with open('assets.cores.json', 'r') as f:
                self.cores_data = json.load(f)
        except FileNotFoundError:
            print("Error: assets.cores.json not found!")
            exit(1)

        # Build system mapping
        self.system_mapping = self.get_system_mapping()

    def get_system_mapping(self):
        """Get mapping between system names and their IDs from the database"""
        cursor = self.db_conn.cursor()
        cursor.execute("SELECT id, name, alias FROM systems")
        db_systems = cursor.fetchall()

        # Create mapping for assets.cores.json system names
        mapping = {}

        # Complete mapping for all systems in assets.cores.json
        name_variations = {
            "Arcade": ["Arcade", "arcade"],
            "EasyRPG": ["RPG Maker", "rpg-maker"],
            "NEC - PC Engine - TurboGrafx 16": ["TurboGrafx 16", "turbografx-16"],
            "Nintendo - Nintendo 64": ["Nintendo 64", "nintendo-64"],
            "Nintendo - Virtual Boy": ["Nintendo Virtual Boy", "nintendo-virtual-boy"],
            "Nintendo - GameBoy": ["Nintendo Game Boy", "nintendo-gameboy"],
            "Nintendo - GameBoy Advance": ["Nintendo Game Boy Advance", "nintendo-gameboy-advance"],
            "Nintendo - Nintendo Entertainment System": ["Nintendo Entertainment System (NES)", "nes"],
            "Nintendo - Super Nintendo Entertainment System": ["Super Nintendo Entertainment System (SNES)", "snes"],
            "Nintendo - GameCube - Wii": ["Nintendo GameCube", "gamecube"],
            "Nintendo - Nintendo 3DS": ["Nintendo 3DS", "nintendo-3ds"],
            "Nintendo - Pokemon Mini": ["Nintendo Pokémon Mini", "pokemon-mini"],

            "Sega - Master System - Mark III": ["Sega Master System", "master-system"],
            "Sega - Mega Drive - Genesis": ["Sega Mega Drive", "genesis"],
            "Sega - Game Gear": ["Sega Game Gear", "game-gear"],
            "Sega - Saturn": ["Sega Saturn", "saturn"],
            "Sega - Dreamcast": ["Sega Dreamcast", "dreamcast"],

            "Sony - PlayStation": ["Sony Playstation", "playstation"],
            "Sony - PlayStation Portable": ["Sony Playstation Portable", "psp"],

            "Bandai - WonderSwan Color": ["WonderSwan Color", "wonderswan-color"],
            "SNK - Neo Geo Pocket": ["Neo Geo Pocket", "neo-geo-pocket"],
            "Coleco - Colecovision": ["Colecovision", "colecovision"],
            "Mattel - Intellivision": ["Intellivision", "intellivision"],
            "GCE - Vectrex": ["Vectrex", "vectrex"],
            "Atari - 2600": ["Atari 2600", "atari-2600"],
            "NEC - PC Engine SuperGrafx": ["PC Engine SuperGrafx", "supergrafx"],

            # Special platforms and engines
            "CHIP-8": ["CHIP-8", "chip-8"],
            "DOS": ["DOS", "ms-dos"],
            "ScummVM": ["ScummVM", "scummvm"],
            "TIC-80": ["TIC-80", "tic-80"],
            "WASM-4": ["WASM-4", "wasm-4"],
            "LowResNX": ["LowRes NX", "lowres-nx"],
            "VaporSpec": ["VaporSpec", "vaporspec"],
            "Uzebox": ["Uzebox", "uzebox"],
            "ChaiLove": ["ChaiLove", "chailove"],
            "Lutro": ["Lutro", "lutro"],
            "Cave Story": ["Cave Story", "cave-story"],
            "Quake": ["Quake", "quake"],
            "Quake II": ["Quake II", "quake-2"],
            "DOOM": ["DOOM", "doom"],
            "Wolfenstein 3D": ["Wolfenstein 3D", "wolfenstein-3d"],
            "Tomb Raider": ["Tomb Raider", "tomb-raider"],
            "Cannonball": ["Cannonball", "cannonball"],
            "Rick Dangerous": ["Rick Dangerous", "rick-dangerous"],
            "Dinothawr": ["Dinothawr", "dinothawr"],
            "Super Bros War": ["Super Bros War", "super-bros-war"],
            "Vircon32": ["Vircon32", "vircon32"],

            # Utilities and misc
            "Utilities": ["Utilities", "utils"],
            "MicroW8": ["MicroW8", "micro-w8"],
            "PocketCDG": ["PocketCDG", "pocket-cdg"],
            "Jump 'n Bump": ["Jump 'n Bump", "jump-n-bump"],
            "Video": ["Video Player", "video-player"],
            "Arduous": ["Arduino", "arduino"],
            "Images": ["Image Viewer", "image-viewer"],
            "Handheld Electronic Game": ["Handheld Electronic Games (LCD)", "lcd-games"]
        }

        # First try to map the systems we know about
        for system in self.cores_data:
            system_name = system['name']
            found = False

            # Try name variations first
            if system_name in name_variations:
                variations = name_variations[system_name]
                for db_system in db_systems:
                    if db_system['name'].lower() in [v.lower() for v in variations] or \
                       db_system['alias'] in variations:
                        mapping[system_name] = db_system['id']
                        print(f"Mapped '{system_name}' to database system '{db_system['name']}' (ID: {db_system['id']})")
                        found = True
                        break

            # If no variation match, try direct match
            if not found:
                for db_system in db_systems:
                    if system_name.lower() == db_system['name'].lower() or \
                       system_name.lower() == db_system['alias']:
                        mapping[system_name] = db_system['id']
                        print(f"Mapped '{system_name}' to database system '{db_system['name']}' (ID: {db_system['id']})")
                        found = True
                        break

            # If still no match, try fuzzy matching
            if not found:
                print(f"Warning: No mapping found for system '{system_name}'")
                db_system_names = [s['name'].lower() for s in db_systems]
                matches = get_close_matches(system_name.lower(), db_system_names, n=1, cutoff=0.6)
                if matches:
                    for db_system in db_systems:
                        if db_system['name'].lower() == matches[0]:
                            mapping[system_name] = db_system['id']
                            print(f"Fuzzy mapped '{system_name}' to database system '{db_system['name']}' (ID: {db_system['id']})")
                            break

        return mapping

    def get_artwork_urls(self, game_id):
        cursor = self.db_conn.cursor()
        cursor.execute("""
            SELECT filename, type
            FROM game_artwork
            WHERE game_id = ?
            AND (type = 'boxart' OR type = 'screenshot')
            ORDER BY type, id
        """, (game_id,))
        return cursor.fetchall()

    def download_file(self, url, output_path):
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            block_size = 8192

            with open(output_path, 'wb') as f, tqdm(
                desc=output_path.name,
                total=total_size,
                unit='iB',
                unit_scale=True
            ) as pbar:
                for data in response.iter_content(block_size):
                    size = f.write(data)
                    pbar.update(size)

            # Small delay to prevent overwhelming the server
            time.sleep(0.5)
            return True

        except requests.exceptions.RequestException as e:
            print(f"Error downloading {url}: {e}")
            return False

    def download_artwork_parallel(self, system_name, original_filename, game_title, artwork_urls, max_workers=4):
        """Download artwork for a game using parallel downloads"""
        base_path = Path("ROMs") / system_name
        base_path.mkdir(parents=True, exist_ok=True)

        # Use original filename (minus extension) for the output files
        safe_title = os.path.splitext(original_filename)[0]

        # Prepare download tasks
        download_tasks = []
        for url_data in artwork_urls:
            cdn_url = f"{GAMESDB_CDN}images/original/{url_data['filename']}"

            if url_data['type'] == 'boxart':
                output_path = base_path / f"{safe_title}-cover.jpg"
            else:  # screenshot
                output_path = base_path / f"{safe_title}-screenshot.jpg"

            if not output_path.exists():
                download_tasks.append((cdn_url, output_path))

        if not download_tasks:
            return

        # Download files in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(self.download_file, url, path)
                      for url, path in download_tasks]
            concurrent.futures.wait(futures)

    def get_system_games(self, system_id):
        """Get all games for a given system"""
        cursor = self.db_conn.cursor()
        cursor.execute("""
            SELECT id, game_title
            FROM games
            WHERE platform = ?
        """, (system_id,))
        return cursor.fetchall()

    def get_core_games(self):
        """Get list of games from assets.cores.json"""
        games_set = set()

        for system in self.cores_data:
            if 'children' in system:
                for child in system['children']:
                    if child['type'] == 'file':
                        # Clean up the filename to match possible database names
                        game_name = os.path.splitext(child['name'])[0]  # Remove extension
                        game_name = game_name.replace('_', ' ')  # Replace underscores with spaces
                        game_name = re.sub(r'\([^)]*\)', '', game_name)  # Remove parentheses and their contents
                        game_name = game_name.strip()
                        games_set.add(game_name.lower())

        return games_set

    def clean_game_name(self, name):
        """Clean game name for database searching"""
        # Remove file extension
        name = os.path.splitext(name)[0]

        # Remove common suffixes in parentheses
        name = re.sub(r'\s*\([^)]*\)\s*$', '', name)

        # Convert underscores to spaces
        name = name.replace('_', ' ')

        # Add spaces to camelCase words
        name = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)

        # Remove platform-specific suffixes
        suffixes = [
            '-latest',
            'by MooglyGuy (PD)',
            '_Win64',
            '(Nintendo, Wide Screen)',
            '(VTech, Time & Fun)',
            '(Gakken, LCD Card Game)',
            '(Tomytronic)',
            '(Nintendo, Panorama Screen)',
            '(Nintendo, Table Top)',
            '(Mattel Electronics)',
            '(VTech, Electronic Tini-Arcade)',
            '(VTech, Sporty Time & Fun)',
            '(VTech, Explorer Time & Fun)',
            '(Bandai, LSI Game Double Play)'
        ]

        for suffix in suffixes:
            name = name.replace(suffix, '')

        # Clean up any multiple spaces
        name = ' '.join(name.split())

        return name.strip()

    def find_game_in_db(self, game_name, system_id):
        """Find a game in the database using exact match first, then fuzzy match"""
        cursor = self.db_conn.cursor()
        clean_name = self.clean_game_name(game_name)

        # Try exact match first
        cursor.execute("""
            SELECT id, game_title
            FROM games
            WHERE platform = ?
            AND LOWER(game_title) = LOWER(?)
        """, (system_id, clean_name))

        result = cursor.fetchone()
        if result:
            return result

        # If no exact match, try LIKE match
        cursor.execute("""
            SELECT id, game_title
            FROM games
            WHERE platform = ?
            AND LOWER(game_title) LIKE LOWER(?)
        """, (system_id, f"%{clean_name}%"))

        return cursor.fetchone()

    def run(self):
        """Main execution method"""
        for system in self.cores_data:
            system_name = system['name']
            system_id = self.system_mapping.get(system_name)

            if not system_id:
                print(f"Skipping {system_name}: No system ID mapping found")
                continue

            print(f"\nProcessing system: {system_name} (ID: {system_id})")

            if 'children' not in system:
                continue

            for child in tqdm(system['children'], desc=f"Processing {system_name} games"):
                if child['type'] != 'file':
                    continue

                game = self.find_game_in_db(child['name'], system_id)

                if game:
                    artwork_urls = self.get_artwork_urls(game['id'])
                    if artwork_urls:
                        # Pass both original filename and game title
                        self.download_artwork_parallel(system_name, child['name'], game['game_title'], artwork_urls)
                    else:
                        print(f"No artwork found for: {game['game_title']}")
                else:
                    print(f"Could not find game in database: {child['name']}")

                # Small delay between games to prevent overwhelming the server
                time.sleep(0.1)

    def __del__(self):
        if hasattr(self, 'db_conn'):
            self.db_conn.close()

def main():
    parser = argparse.ArgumentParser(description='Download ROMs and/or artwork')
    parser.add_argument('--artwork-only', action='store_true',
                       help='Download only artwork, skip ROM downloads')
    args = parser.parse_args()

    try:
        downloader = ROMDownloader(artwork_only=args.artwork_only)
        downloader.run()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
