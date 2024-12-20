#!/usr/bin/env python3
import os
import json
from pathlib import Path
from typing import Dict, List
from datetime import datetime

def generate_html(mapping: Dict, base_path: str) -> str:
    """Generate HTML index of ROMs"""
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>ROMs Index</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .system {{ margin-bottom: 20px; }}
            .system-header {{
                background: #f0f0f0;
                padding: 10px;
                cursor: pointer;
                user-select: none;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            .system-header:hover {{ background: #e0e0e0; }}
            .system-content {{
                display: block;
                margin-left: 20px;
                overflow-x: auto;
            }}
            .caret {{
                transition: transform 0.2s;
                font-size: 20px;
            }}
            .collapsed .caret {{
                transform: rotate(-90deg);
            }}
            .collapsed + .system-content {{
                display: none;
            }}
            .rom-row {{
                display: flex;
                align-items: center;
                padding: 10px;
                border-bottom: 1px solid #eee;
            }}
            .rom-info {{ flex: 1; }}
            .artwork {{
                max-width: 100px;
                max-height: 100px;
                margin: 0 10px;
            }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{
                padding: 8px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }}
            th {{ background-color: #f5f5f5; }}
            .size {{ color: #666; }}
            .timestamp {{ color: #999; font-size: 0.8em; }}
        </style>
        <script>
            function toggleSystem(systemId) {{
                const header = document.querySelector(`[data-system="${{systemId}}"]`);
                header.classList.toggle('collapsed');
            }}
        </script>
    </head>
    <body>
        <h1>ROMs Index</h1>
        <p class="timestamp">Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    """

    for system_name, system_data in sorted(mapping.items()):
        system_id = system_name.replace('.', '_')
        html += f"""
        <div class="system">
            <div class="system-header" data-system="{system_id}" onclick="toggleSystem('{system_id}')">
                <span>📁 {system_name} ({system_data['count']} ROMs)</span>
                <span class="caret">▼</span>
            </div>
            <div class="system-content" id="{system_id}">
                <table>
                    <tr>
                        <th>ROM</th>
                        <th>Size</th>
                        <th>Artwork</th>
                    </tr>
        """

        for rom in system_data['roms']:
            size_kb = rom['size'] / 1024
            size_mb = size_kb / 1024
            size_str = f"{size_mb:.2f} MB" if size_mb >= 1 else f"{size_kb:.2f} KB"

            rom_path = f"ROMs/{system_name}/{rom['file']}"
            artwork_html = ""

            if 'artwork' in rom:
                if 'cover' in rom['artwork']:
                    cover_path = f"ROMs/{system_name}/{rom['artwork']['cover']}"
                    artwork_html += f'<a href="{cover_path}"><img src="{cover_path}" class="artwork" alt="Cover" title="Cover"></a>'
                if 'screenshot' in rom['artwork']:
                    screenshot_path = f"ROMs/{system_name}/{rom['artwork']['screenshot']}"
                    artwork_html += f'<a href="{screenshot_path}"><img src="{screenshot_path}" class="artwork" alt="Screenshot" title="Screenshot"></a>'

            html += f"""
                    <tr>
                        <td><a href="{rom_path}">{rom['file']}</a></td>
                        <td class="size">{size_str}</td>
                        <td>{artwork_html}</td>
                    </tr>
            """

        html += """
                </table>
            </div>
        </div>
        """

    html += """
    </body>
    </html>
    """

    return html

def scan_roms_folder(base_path: str) -> Dict:
    """Scan ROMs folder and generate mapping of contents"""
    base = Path(base_path)
    mapping = {}

    # Scan each system folder
    for system_dir in base.iterdir():
        if not system_dir.is_dir():
            continue

        system_name = system_dir.name
        roms_list = []
        rom_count = 0

        # Scan contents of system folder
        for file_path in system_dir.iterdir():
            # Process ROM files (zip and dosz files)
            if file_path.suffix.lower() not in ['.zip', '.dosz']:
                continue

            rom_count += 1
            rom_base = file_path.stem
            rom_info = {
                "file": file_path.name,
                "size": file_path.stat().st_size
            }

            # Check for artwork
            artwork = {}
            cover_path = file_path.with_name(f"{rom_base}-cover.jpg")
            screenshot_path = file_path.with_name(f"{rom_base}-screenshot.jpg")

            if cover_path.exists():
                artwork["cover"] = cover_path.name
            if screenshot_path.exists():
                artwork["screenshot"] = screenshot_path.name

            if artwork:
                rom_info["artwork"] = artwork

            roms_list.append(rom_info)

        # Add system to mapping if it has ROMs
        if rom_count > 0:
            mapping[system_name] = {
                "count": rom_count,
                "roms": roms_list
            }

    return mapping

def main():
    # Assuming ROMs folder is in current directory
    roms_path = "ROMs"

    if not os.path.exists(roms_path):
        print(f"Error: {roms_path} directory not found")
        return

    print(f"Scanning {roms_path}...")
    mapping = scan_roms_folder(roms_path)

    # Write to JSON file
    output_file = "roms_mapping.json"
    with open(output_file, 'w') as f:
        json.dump(mapping, f, indent=2)

    # Generate and write HTML index
    html_content = generate_html(mapping, roms_path)
    with open('index.html', 'w') as f:
        f.write(html_content)

    # Print summary
    total_roms = sum(system["count"] for system in mapping.values())
    total_systems = len(mapping)
    print(f"\nFound {total_roms} ROMs across {total_systems} systems")
    print(f"Mapping written to {output_file}")
    print(f"HTML index written to index.html")

if __name__ == "__main__":
    main()
