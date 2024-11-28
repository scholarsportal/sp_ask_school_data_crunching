# Windows Setup Guide

Detailed guide for setting up sp-ask-school-data-crunching on Windows.

## System Requirements

- Windows 10 or higher
- Python 3.10+
- Poetry package manager

## Installation Steps

1. Install Poetry:
```powershell
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
```

2. Set up LibraryH3lp configuration:

   a. Open PowerShell as administrator:
   ```powershell
   # Create .lh3 directory
   $lh3Path = "$env:USERPROFILE\.lh3"
   New-Item -ItemType Directory -Force -Path $lh3Path
   ```

   b. Create config file:
   ```powershell
   @"
[default]
scheme = https
server = libraryh3lp.com
timezone = UTC
version = v2
"@ | Out-File -FilePath "$lh3Path\config" -Encoding UTF8
   ```

   c. Create credentials file:
   ```powershell
   @"
[default]
username = your_username
password = your_password
"@ | Out-File -FilePath "$lh3Path\credentials" -Encoding UTF8
   ```

## Troubleshooting

### Common Windows Issues

1. File Permission Issues:
   ```powershell
   # Check file permissions
   Get-Acl "$env:USERPROFILE\.lh3\credentials"
   
   # Set appropriate permissions
   $acl = Get-Acl "$env:USERPROFILE\.lh3\credentials"
   $acl.SetAccessRuleProtection($true, $false)
   Set-Acl "$env:USERPROFILE\.lh3\credentials" $acl
   ```

2. Path Issues:
   - Make sure PATH environment variable includes Python and Poetry
   - Use full paths when referencing files

3. File Extension Issues:
   ```powershell
   # Remove .txt extension if present
   Get-ChildItem "$env:USERPROFILE\.lh3" | 
   Where-Object { $_.Name -like "*.txt" } |
   Rename-Item -NewName { $_.Name -replace '\.txt$','' }
   ```

## Testing Installation

1. Open PowerShell:
```powershell
# Create and activate virtual environment
poetry install
poetry shell

# Test configuration
python -c "from sp_ask_school_data_crunching import analyze_school; analyze_school('University of Toronto', '2024-01-01', '2024-01-02')"
```

## Getting Help

If you encounter issues:
1. Check the configuration files exist and have correct content
2. Verify PowerShell execution policy allows running scripts
3. Contact support with error messages and logs