import pandas as pd
import numpy as np
import re
import requests
import warnings
warnings.filterwarnings('ignore')

# =============================================================================
# CONFIGURATION — just add new (filepath, industry) pairs here
# =============================================================================
FILES = [
    ("Melb_Hospitality.csv", "Hospitality"),
    ("Hospitality.csv", "Hospitality"),
    ("Retail.csv", "Retail"),
    # Add more here, e.g.:
    # ("Construction.csv", "Construction"),
    # ("Healthcare.csv", "Healthcare"),
    # ("Education.csv", "Education"),
]
OUTPUT_FILE = "Merged_Business_Data.csv"


# =============================================================================
# EMAIL SCRAPING (optional)
# =============================================================================
def extract_email_from_website(url):
    if pd.isna(url) or url == "":
        return None
    url = str(url).strip()
    if not url.startswith('http'):
        url = 'https://' + url
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        text = response.text
        mailto = re.findall(r'mailto:([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', text)
        if mailto:
            return mailto[0]
        exclude = ['example.com', 'domain.com', 'yourdomain', 'email@', '@gmail.com',
                   '@yahoo.com', '@hotmail.com']
        matches = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
        for match in matches:
            if not any(ex in match.lower() for ex in exclude):
                return match
        return None
    except Exception:
        return None


# =============================================================================
# SUBURB EXTRACTION
# =============================================================================
def extract_suburb(addr):
    if pd.isna(addr):
        return None
    match = re.search(r',\s*([A-Za-z\s]+)\s+VIC\s+\d{4}\s*,\s*Australia', str(addr))
    if match:
        return match.group(1).strip()
    match = re.search(r',\s*([^,]+?)\s+VIC', str(addr))
    if match:
        return match.group(1).strip()
    return None


# =============================================================================
# MAIN PROCESSING
# =============================================================================
def process_file(filepath, industry, scrape_emails=False):
    print(f"\nProcessing: {filepath} (Industry: {industry})")
    df = pd.read_csv(filepath)
    print(f"  Loaded {len(df)} rows, {len(df.columns)} columns")

    # Rename core columns
    rename_map = {
        'url': 'Google Maps',
        'title': 'Business Name',
        'categoryName': 'Category',
        'address': 'Address',
        'website': 'Website',
        'location/lat': 'Latitude',
        'location/lng': 'Longitude',
        'permanentlyClosed': 'Permanently Closed',
        'phone': 'Phone',
        'reviewsCount': 'Reviews Count',
        'totalScore': 'Total Score'
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
    df['Industry'] = industry

    # Opening hours → Mon-Sun
    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    for day in days:
        df[day] = ''

    for i in range(7):
        day_col = f'openingHours/{i}/day'
        hours_col = f'openingHours/{i}/hours'
        if day_col in df.columns and hours_col in df.columns:
            for idx, row in df.iterrows():
                day_name = str(row[day_col]).strip() if pd.notna(row[day_col]) else None
                hours = str(row[hours_col]).strip() if pd.notna(row[hours_col]) else ''
                hours = hours.replace('\u202f', ' ')
                if day_name:
                    day_abbr = day_name[:3].capitalize()
                    if day_abbr in days:
                        df.at[idx, day_abbr] = hours

    df = df.drop(columns=[c for c in df.columns if c.startswith('openingHours')], errors='ignore')

    # Combine accessibility columns
    acc_cols = [c for c in df.columns if 'Accessibility' in c]
    feature_groups = {}
    for col in acc_cols:
        match = re.match(r'additionalInfo/Accessibility/\d+/(.*)', col)
        if match:
            feature_groups.setdefault(match.group(1), []).append(col)

    for feature, cols in feature_groups.items():
        clean_name = feature.title()
        bool_df = df[cols].copy()
        for c in cols:
            bool_df[c] = bool_df[c].map({
                'true': True, 'True': True, True: True,
                'false': False, 'False': False, False: False
            }).fillna(False).astype(bool)
        df[clean_name] = bool_df.any(axis=1)
        df = df.drop(columns=cols, errors='ignore')

    # Drop the two hyphenated accessibility columns
    for col in ['Wheelchair-Accessible Entrance', 'Wheelchair-Accessible Car Park']:
        if col in df.columns:
            df = df.drop(columns=[col])
            print(f"  Dropped: {col}")

    # Suburb
    df['Suburb'] = df['Address'].apply(extract_suburb)

    # Drop junk
    junk = [c for c in df.columns if any(p in c for p in ['additionalInfo/', 'categories/', 'openingHours/'])]
    df = df.drop(columns=junk, errors='ignore')

    # Email
    df['Email'] = None
    if scrape_emails:
        print("  Scraping emails...")
        df['Email'] = df['Website'].apply(extract_email_from_website)
        print(f"  Found {df['Email'].notna().sum()} emails")

    # Capitalize
    df.columns = [c[0].upper() + c[1:] if c else c for c in df.columns]

    # Reorder
    base = ['Industry', 'Business Name', 'Category', 'Address', 'Suburb',
            'Google Maps', 'Website', 'Email', 'Phone',
            'Latitude', 'Longitude', 'Permanently Closed',
            'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    extras = [c for c in df.columns if c not in base + ['Reviews Count', 'Total Score']]
    order = [c for c in base if c in df.columns] + extras + ['Reviews Count', 'Total Score']
    df = df[[c for c in order if c in df.columns]]

    print(f"  Final shape: {df.shape}")
    return df


# =============================================================================
# RUN — loops over all files automatically
# =============================================================================
if __name__ == "__main__":
    processed = []
    for filepath, industry in FILES:
        df = process_file(filepath, industry, scrape_emails=False)
        processed.append(df)

    print("\n--- Merging ---")
    all_cols = set().union(*[set(d.columns) for d in processed])
    for df in processed:
        for col in all_cols:
            if col not in df.columns:
                df[col] = None

    common_cols = list(processed[0].columns)
    merged = pd.concat([d[common_cols] for d in processed], ignore_index=True)
    print(f"Before deduplication: {len(merged)} rows")

    before = len(merged)
    merged = merged.drop_duplicates(subset=['Address'], keep='first')
    print(f"Removed {before - len(merged)} duplicate rows")
    print(f"After deduplication: {len(merged)} rows")

    merged.to_csv(OUTPUT_FILE, index=False, encoding = 'utf-8-sig')
    print(f"\n✅ Saved to: {OUTPUT_FILE}")
    print(f"   {len(merged)} rows × {len(merged.columns)} columns")