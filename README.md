# macOS Alias-Aware Copy

This tool copies a macOS folder to another folder and replaces any Finder alias
files with the real target content, while keeping the alias filenames.

## Requirements

- macOS (Finder alias resolution relies on AppleScript)
- Python 3

The first run may trigger a macOS Automation prompt for Finder access.

## Usage

```bash
python3 copy_aliases.py /path/to/source /path/to/destination
```

Optional verbose output:

```bash
python3 copy_aliases.py -v /path/to/source /path/to/destination
```

## Behavior

- Regular files and folders are copied as-is.
- Finder alias files are resolved and replaced by the alias target content.
- The destination keeps the alias filename (or folder name), while preserving the
  target file extension.
- Aliases that point to folders are copied as full directories.
- If an alias cannot be resolved, the alias file itself is copied and a warning
  is printed to stderr.

## Notes

- The destination cannot be inside the source directory.
