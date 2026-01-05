# LinkedIn Data Scientist Job Finder
Automatically collect job listings for "Data Scientist" in Israel via LinkedIn

## Installation

### Prerequisites
- Python 3.8 or higher
- Chrome browser

### Setup
1. **Clone this repo:**
```bash
git clone ---
cd linkedin_job_search
```
2. **Install the following packages:**
```bash
pip install -r requirements.txt
```
(The versions listed are the versions installed on my machine)

### Usage
Start the web server with automatic updating CSV every 12 hours:
```bash
python web_server.py
```
Then open browser to: http://localhost:5000

You will see the job listings table, download button for the CSV file, and a countdown to the next file update.

## Technical Details
### Python Packages used
- **Selenium**: Browser automation
- **BeautifulSoup**: HTML parsing
- **Flask**: Web server
- **APScheduler**: Task scheduling
- **Pandas**: Data processing

### Process
#### find_jobs.py:
1. Open browser in headless mode (no GUI)
2. Search LinkedIn for jobs as "data scientist" in Israel
3. Scroll to collect maximum available number of listings
4. Visit each job listing link to extract job title, company, location, and description
5. Look for language patterns for degree requirements and years of experience requirements using regex
6. Save job data to CSV file while checking to prevent multiplications

#### scheduler.py:
Run job finder function from find_jobs.py every set interval and update next run time to be current time plus interval

#### web_server.py:
1. On opening, html template is rendered with heading, info box with the number of jobs, companies, last CSV update, next scheduled CSV update, countdown to the next update and button to download the CSV file, and a table with headings of job title, company, location, degree, experience, link and date retrieved
2. On pressing download button, the CSV file is downloaded with file time containing current date

## Limitations
- The degree and experience extraction is relatively crude due to varyations in the job description texts
- LinkedIn user is not signed in and therefore very a limited number of jobs is available