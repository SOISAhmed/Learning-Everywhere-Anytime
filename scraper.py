# CPALMS Web Scraping Strategy for Florida Standards
# Two approaches: API (preferred) + Web Scraping (backup)

import requests
import json
import time
import sqlite3
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urljoin, quote
import re
from typing import List, Dict, Optional

class CPALMSDataCollector:
  """
    Collects Florida Standards data from CPALMS using API (preferred) or web scraping
    """

def __init__(self, api_key: Optional[str] = None):
  self.api_key = api_key
self.base_url = "https://www.cpalms.org"
self.api_base_url = "https://www.cpalms.org/api"  # Need to verify actual endpoint
self.search_url = "https://www.cpalms.org/search/Standard"
self.session = requests.Session()

# Set headers to avoid being blocked
self.session.headers.update({
  'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
  'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
  'Accept-Language': 'en-US,en;q=0.5',
  'Accept-Encoding': 'gzip, deflate',
  'Connection': 'keep-alive',
  'Upgrade-Insecure-Requests': '1',
})

# Rate limiting
self.request_delay = 2  # seconds between requests

def setup_database(self, db_path: str = "florida_standards.db"):
  """Create SQLite database for storing standards"""
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute('''
            CREATE TABLE IF NOT EXISTS standards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                standard_id TEXT UNIQUE,
                state TEXT DEFAULT 'FL',
                subject TEXT,
                grade TEXT,
                domain TEXT,
                cluster TEXT,
                title TEXT,
                description TEXT,
                clarifications TEXT,
                keywords TEXT,  -- JSON array
                url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

cursor.execute('''
            CREATE TABLE IF NOT EXISTS scraping_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT,
                grade TEXT,
                status TEXT,
                records_collected INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT
            )
        ''')

conn.commit()
conn.close()

def get_subjects_and_grades(self) -> Dict:
  """Extract available subjects and grades from the search page"""
try:
  response = self.session.get(self.search_url)
response.raise_for_status()
soup = BeautifulSoup(response.content, 'html.parser')

# This would need to be adjusted based on actual HTML structure
# For now, return the subjects we know exist
subjects = [
  "English Language Arts (B.E.S.T.)",
  "Mathematics (B.E.S.T.)",
  "Science",
  "Social Studies",
  "Health Education",
  "Physical Education",
  "Visual Art",
  "Music",
  "Theatre",
  "Dance",
  "World Languages",
  "Computer Science (Starting 2025-2026)"
]

grades = ["K", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]

return {"subjects": subjects, "grades": grades}

except requests.RequestException as e:
  print(f"Error fetching subjects and grades: {e}")
return {"subjects": [], "grades": []}

def scrape_standards_by_subject_grade(self, subject: str, grade: str) -> List[Dict]:
  """
        Scrape standards for a specific subject and grade
        This is a template - actual implementation would need to be adjusted
        based on the real CPALMS search results structure
        """
standards = []

try:
  # Construct search URL with parameters
  params = {
    'subject': subject,
    'grade': grade,
    # Add other parameters as needed
  }

response = self.session.get(self.search_url, params=params)
response.raise_for_status()
soup = BeautifulSoup(response.content, 'html.parser')

# This would need to be adjusted based on actual HTML structure
# Looking for standard cards/items in the results
standard_elements = soup.find_all('div', class_='standard-item')  # Hypothetical class

for element in standard_elements:
  try:
  standard_data = self.extract_standard_data(element, subject, grade)
if standard_data:
  standards.append(standard_data)
except Exception as e:
  print(f"Error extracting standard data: {e}")
continue

# Respect rate limiting
time.sleep(self.request_delay)

except requests.RequestException as e:
  print(f"Error scraping {subject} - Grade {grade}: {e}")

return standards

def extract_standard_data(self, element, subject: str, grade: str) -> Optional[Dict]:
  """Extract individual standard data from HTML element"""
try:
  # This would need to be adjusted based on actual HTML structure
  standard_id = element.find('span', class_='standard-id')
title = element.find('h3', class_='standard-title')
description = element.find('div', class_='standard-description')

if not all([standard_id, title, description]):
  return None

# Extract keywords from description
keywords = self.extract_keywords(description.get_text())

return {
  'standard_id': standard_id.get_text().strip(),
  'subject': subject,
  'grade': grade,
  'title': title.get_text().strip(),
  'description': description.get_text().strip(),
  'keywords': json.dumps(keywords),
  'url': urljoin(self.base_url, element.find('a')['href']) if element.find('a') else None
}

except Exception as e:
  print(f"Error extracting standard data: {e}")
return None

def extract_keywords(self, text: str) -> List[str]:
  """Extract relevant keywords from standard description"""
# Simple keyword extraction - could be improved with NLP
stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'a', 'an'}

# Clean text and extract words
words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
keywords = [word for word in words if word not in stop_words]

# Return unique keywords, limited to most frequent
return list(set(keywords))[:20]

def save_standards_to_db(self, standards: List[Dict], db_path: str = "florida_standards.db"):
  """Save collected standards to database"""
if not standards:
  return

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

for standard in standards:
  try:
  cursor.execute('''
                    INSERT OR REPLACE INTO standards 
                    (standard_id, subject, grade, title, description, keywords, url)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                  standard['standard_id'],
                  standard['subject'],
                  standard['grade'],
                  standard['title'],
                  standard['description'],
                  standard['keywords'],
                  standard.get('url')
                ))
except Exception as e:
  print(f"Error saving standard {standard.get('standard_id', 'unknown')}: {e}")

conn.commit()
conn.close()

def log_scraping_activity(self, subject: str, grade: str, status: str, 
                          records_collected: int, notes: str = ""):
  """Log scraping activity for monitoring"""
conn = sqlite3.connect("florida_standards.db")
cursor = conn.cursor()

cursor.execute('''
            INSERT INTO scraping_log (subject, grade, status, records_collected, notes)
            VALUES (?, ?, ?, ?, ?)
        ''', (subject, grade, status, records_collected, notes))

conn.commit()
conn.close()

def collect_all_standards(self, focus_subjects: List[str] = None, 
                          focus_grades: List[str] = None):
  """
        Main method to collect all standards
        """
print("Setting up database...")
self.setup_database()

print("Getting available subjects and grades...")
available = self.get_subjects_and_grades()

subjects_to_scrape = focus_subjects or available['subjects']
grades_to_scrape = focus_grades or available['grades']

print(f"Planning to scrape {len(subjects_to_scrape)} subjects × {len(grades_to_scrape)} grades")

total_collected = 0

for subject in subjects_to_scrape:
  for grade in grades_to_scrape:
  print(f"\nScraping {subject} - Grade {grade}...")

try:
  standards = self.scrape_standards_by_subject_grade(subject, grade)

if standards:
  self.save_standards_to_db(standards)
total_collected += len(standards)
print(f"  ✓ Collected {len(standards)} standards")

self.log_scraping_activity(
  subject, grade, "success", len(standards)
)
else:
  print(f"  ⚠ No standards found")
self.log_scraping_activity(
  subject, grade, "no_data", 0, "No standards found"
)

except Exception as e:
  print(f"  ✗ Error: {e}")
self.log_scraping_activity(
  subject, grade, "error", 0, str(e)
)

print(f"\n🎉 Collection complete! Total standards collected: {total_collected}")
return total_collected

# Alternative approach: API-based collection (if you get API access)
class CPALMSAPICollector:
  """
    Collects Florida Standards using the official CPALMS API
    Requires API key from CPALMS
    """

def __init__(self, api_key: str):
  self.api_key = api_key
# Note: These URLs are hypothetical - would need to be confirmed
self.case_api_url = "https://api.cpalms.org/case/v1p0"
self.session = requests.Session()
self.session.headers.update({
  'Authorization': f'Bearer {api_key}',
  'Content-Type': 'application/json'
})

def get_standards_via_api(self) -> List[Dict]:
  """
        Fetch standards using the CASE API format
        This is a template - actual implementation would depend on API documentation
        """
try:
  # Get the competency framework
  response = self.session.get(f"{self.case_api_url}/CFDocuments")
response.raise_for_status()

documents = response.json()
standards = []

for doc in documents.get('CFDocuments', []):
  if 'Florida' in doc.get('title', ''):
  # Get competencies for this document
  comp_response = self.session.get(
    f"{self.case_api_url}/CFDocuments/{doc['identifier']}/CFItems"
  )
comp_response.raise_for_status()

competencies = comp_response.json()
standards.extend(self.parse_case_competencies(competencies))

return standards

except requests.RequestException as e:
  print(f"API Error: {e}")
return []

def parse_case_competencies(self, competencies: Dict) -> List[Dict]:
  """Parse CASE format competencies into our standard format"""
standards = []

for item in competencies.get('CFItems', []):
  standard = {
    'standard_id': item.get('humanCodingScheme', ''),
    'title': item.get('abbreviatedStatement', ''),
    'description': item.get('fullStatement', ''),
    'subject': self.extract_subject(item),
    'grade': self.extract_grade(item),
    'keywords': json.dumps(self.extract_keywords_from_case(item))
  }
standards.append(standard)

return standards

def extract_subject(self, item: Dict) -> str:
  """Extract subject from CASE item"""
# Implementation would depend on CASE structure
return item.get('CFDocumentURI', {}).get('title', '').split(' ')[0]

def extract_grade(self, item: Dict) -> str:
  """Extract grade from CASE item"""
# Implementation would depend on CASE structure
education_level = item.get('educationLevel', [''])
return education_level[0] if education_level else ''

def extract_keywords_from_case(self, item: Dict) -> List[str]:
  """Extract keywords from CASE item"""
text = f"{item.get('fullStatement', '')} {item.get('abbreviatedStatement', '')}"
return self.extract_keywords(text)

# Usage examples and testing
def main():
  """Example usage of the CPALMS data collector"""

# Option 1: Web scraping approach (no API key needed)
print("=== Web Scraping Approach ===")
scraper = CPALMSDataCollector()

# Start with a focused collection for testing
focus_subjects = ["English Language Arts (B.E.S.T.)", "Mathematics (B.E.S.T.)"]
focus_grades = ["K", "1", "2", "3", "4", "5"]

scraper.collect_all_standards(focus_subjects, focus_grades)

# Option 2: API approach (requires API key)
# api_collector = CPALMSAPICollector("your_api_key_here")
# standards = api_collector.get_standards_via_api()

# Check results
conn = sqlite3.connect("florida_standards.db")
df = pd.read_sql_query("SELECT * FROM standards LIMIT 10", conn)
print("\nSample of collected standards:")
print(df[['standard_id', 'subject', 'grade', 'title']].to_string())
conn.close()

if __name__ == "__main__":
  main()

# Next steps for your prototype:
# 1. Test the scraping approach with a small subset
# 2. Apply for CPALMS API access for production use
# 3. Build the matching algorithm using this data
# 4. Create the web interface

"""
IMPLEMENTATION NOTES:

1. **API Approach (Recommended)**: 
   - Apply for CPALMS API access first
   - Uses CASE standard format
   - More reliable and respectful to CPALMS servers
   - Rate limited to 1 request per day during development

2. **Web Scraping Approach (Backup)**:
   - Inspect the actual CPALMS search results page
   - Adjust the HTML parsing logic based on real structure
   - Be respectful with rate limiting
   - Monitor for changes in website structure

3. **For Your Prototype**:
   - Start with manual data entry for a few example standards
   - Focus on the matching algorithm and UI first
   - Add automated data collection later

4. **Legal Considerations**:
   - CPALMS data is public domain (government standards)
   - Respect their terms of service
   - Consider reaching out to CPALMS team for guidance
"""
