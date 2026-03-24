# Tracked template only — do not rely on this file being imported for the explorer or Streamlit app.
# Copy to scripts/config_secret.py or scripts/config.py (gitignored), then set DATA_FOLDER there.
# Path resolution loads only those two filenames, then the process working directory (see streamlit_app/README.md).
GOOGLE_API_KEY = "REPLACE_WITH_YOUR_KEY"
DATA_FOLDER = "the/path/to/eBird/Data/Folder/"
DEPLOY_DESTINATION = "/path/to/eBirdChecklistNameFromGPS/eBirdChecklistNameFromGPS.py"  # deploy_to_live target

## Example path syntax (cross-platform)
##
## macOS:
##   DATA_FOLDER = "/Users/bobsmith/OneDrive/ebirdData"
##
## Windows (use raw string r"..." or forward slashes — no need to escape backslashes):
##   DATA_FOLDER = r"C:\Users\bobsmith\Documents\ebirdData"
##   DATA_FOLDER = "C:/Users/bobsmith/Documents/ebirdData"
##
