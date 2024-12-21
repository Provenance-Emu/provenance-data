# Provenance Data

_repo to hold test roms, screenshot and index generation scripts_

## How to help

### Add ROMs

- Find a legal!, open-source homebrew or open domain rom
- Rename ambigous extensions, fix spacing and formatting, ie; for Genesis, `my_demo_rom.bin` to `My Demo Rom.gen`
- Zip it in a flat file with no other unrelated files, with the same filename as the game; ie; `My Demo ROM.zip`
- Optionally, but preffered, add artwork. See "Add Artwork"

### Add artwork

- clone this repo
- add artwork in the format (ROMNAME)-screenshot.png/jpg/jpeg or (ROMNAME)-cover.png/jpg/jpeg
- run the generation script
  ```sh
  python scan_roms.py
  ```
-- commit, push, make a pull-request
