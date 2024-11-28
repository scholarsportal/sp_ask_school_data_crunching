# Configuration Guide

This package relies on the LibraryH3lp API (lh3api) for data access. Here's how to set it up:

## Prerequisites

1. LibraryH3lp admin account credentials
2. Python 3.10 or higher installed
3. Poetry package manager installed

## Configuration Files

### Unix-based Systems (Linux/MacOS)

1. Create a `.lh3` directory in your home folder:
```bash
mkdir ~/.lh3
```

2. Create a `config` file:
```bash
touch ~/.lh3/config
```

Add the following content:
```ini
[default]
scheme = https
server = libraryh3lp.com
timezone = UTC
version = v2
```

3. Create a `credentials` file:
```bash
touch ~/.lh3/credentials
```

Add your credentials:
```ini
[default]
username = your_username
password = your_password
```

### Windows Setup

1. Create a `.lh3` directory in your user folder:
```powershell
mkdir $env:USERPROFILE\.lh3
```

2. Create `config` file:
   - Open Notepad
   - Save the following content as `%USERPROFILE%\.lh3\config`:
```ini
[default]
scheme = https
server = libraryh3lp.com
timezone = UTC
version = v2
```

3. Create `credentials` file:
   - Open Notepad
   - Save the following content as `%USERPROFILE%\.lh3\credentials`:
```ini
[default]
username = your_username
password = your_password
```

## Verifying Configuration

Test your configuration:

```python
from sp_ask_school_data_crunching import analyze_school

# Try analyzing a short period
analyzer = analyze_school(
    school_name="University of Toronto",
    start_date="2024-01-01",
    end_date="2024-01-02"
)
```

If successful, you should see data being fetched and visualizations being generated.

## Common Issues

1. "Cannot find credentials":
   - Ensure the `.lh3` directory and files are in your home directory
   - Check file permissions

2. "Authentication failed":
   - Verify your username and password
   - Ensure you have admin access

3. Windows-specific:
   - Make sure files don't have `.txt` extension
   - Use full path if having issues

## Security Notes

1. Keep your credentials secure:
   - Don't commit them to version control
   - Set appropriate file permissions
   - Don't share your credentials

2. API rate limits:
   - Be mindful of date ranges
   - Consider implementing delays for large queries

## Next Steps

Once configured, see [usage.md](usage.md) for examples of how to use the package.

For Windows-specific details, see [windows_setup.md](windows_setup.md).