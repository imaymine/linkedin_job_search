from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import time
import random
import re
from datetime import datetime
import os

"""
JobFinder: A class to scrape job listings from LinkedIn using Selenium automated browser
"""


class JobFinder:
    def __init__(self, headless=True):
        """
        Initialize the JobFinder with Selenium WebDriver.
        
        :param self: 
        :param headless: if True, runs browser in headless mode (without GUI)
        """
        print("Initializing JobFinder...")
        chrome_options = Options()
        # headless - runs without GUI
        # sandbox, dev-shm-usage - for Linux compatability
        # diable-blink - to avoid detection as bot
        # user-agent - to mimic real browser
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebkit/537.36"
        )
        
        # Initialize Webdriver with the options
        # Wait up to 10 seconds for elements to appear
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.implicitly_wait(10)
        print("JobFinder initialized.")

    def search_jobs(self, search_term="data scientist", location="Israel", max_jobs=25):
        """
        Look up max jobs on LinkedIn with the giver search term and location
        
        :param self: 
        :param search_term: Job title to search for
        :param location: Location for filtering
        :param max_jobs: Maximum num of jobs to collect
        
        :return: Set of job URLs
        """
        print(f"Searching for jobs: {search_term} in {location}...")
        # Construct search url using search term and location (replace spaces with %20)
        search_url = f"https://www.linkedin.com/jobs/search/?keywords={search_term.replace(' ', '%20')}&location={location.replace(' ', '%20')}"
        print(f"Search URL: {search_url}")

        self.driver.get(search_url)
        # Random sleep to mimic human behavior
        time.sleep(random.uniform(4, 6))

        job_urls = set()
        # count number of times no new jobs appeared when scrolling so we don't scroll needlessly
        no_new_jobs_cnt = 0

        try:
            for scroll in range(20):
                # Try to scroll down the search, pausing for random times as well as jiggle the scroll to stimulate human behavior and trigger lazy loading mechanisms
                bf_cnt = len(job_urls)
                self.driver.execute_script(
                    "window.scrollTo(0, document.body.scrollHeight);"
                )
                time.sleep(random.uniform(3, 5))
                
                self.driver.execute_script("window.scrollBy(0, -100);")
                time.sleep(random.uniform(0, 1))
                self.driver.execute_script("window.scrollBy(0, 100);")
                time.sleep(random.uniform(0, 1))

                # Get all job listing elements on the page and extract their URLs
                job_listings = self.driver.find_elements(
                    By.CLASS_NAME, "base-card__full-link"
                )

                print(f"Found {len(job_listings)} job listings")

                # Clean job urls, count the number of new jobs found, and if none found in 3 consecutive scrolls, stop scrolling
                for job in job_listings:
                    job_url = job.get_attribute("href")
                    if job_url and "linkedin.com/jobs/view/" in job_url:
                        clean_url = job_url.split("?")[0]
                        job_urls.add(clean_url)
                after_cnt = len(job_urls)
                new_found = after_cnt - bf_cnt
                print(f"Found {new_found} new job URLs, total collected: {after_cnt}")
                
                if new_found == 0:
                    no_new_jobs_cnt += 1
                    if no_new_jobs_cnt >= 3:
                        print("No new jobs found in 3 consecutive scrolls, stopping.")
                        break
                else:
                    no_new_jobs_cnt = 0

                print(f"Collected {len(job_urls)} unique job URLs")

        except Exception as e:
            print(f"Error during job search: {e}")

        return job_urls

    def extract_job_details(self, job_url):
        """
        Visit individual URLs and collect job details
        
        :param self:
        :param job_url: URL of the job listing
        
        :return: job_data dictionary with title, company, location, description (all text) and URL
        """
        print(f"Extracting job details from: {job_url}")
        self.driver.get(job_url)
        # Random sleep to mimic human behavior
        time.sleep(random.uniform(2, 4))

        # Dictionary to hold job info
        job_data = {
            "title": "",
            "company": "",
            "location": "",
            "description": "",
            "job_url": job_url,
        }

        try:
            try:
                # Wait for title element to load and extract text
                title_element = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "h1.top-card-layout__title")
                    )
                )
                job_data["title"] = title_element.text.strip()
            except:
                job_data["title"] = "Not Found"

            try:
                # Extract company name
                company_element = self.driver.find_element(
                    By.CSS_SELECTOR, "a.topcard__org-name-link"
                )
                job_data["company"] = company_element.text.strip()
            except:
                try:
                    company_element = self.driver.find_element(
                        By.CSS_SELECTOR, "span.topcard__flavor"
                    )
                    job_data["company"] = company_element.text.strip()
                except:
                    job_data["company"] = "Not Found"

            try:
                # Extract location
                location_element = self.driver.find_element(
                    By.CSS_SELECTOR, "span.topcard__flavor--bullet"
                )
                job_data["location"] = location_element.text.strip()
            except:
                job_data["location"] = "Israel"

            try:
                try:
                    # Try to expend job desc with show more button
                    show_more_button = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable(
                            (By.CSS_SELECTOR, "button.show-more-less-html__button")
                        )
                    )
                    show_more_button.click()
                    time.sleep(1)
                except:
                    pass
                # Try multiple possible CSS containers for the description
                container = None
                desc_container = [
                    "div.show-more-less-html__markup",
                    "div.description__text",
                    "div.jobs-description__content",
                ]

                # Match one of the container types 
                for selector in desc_container:
                    try:
                        container = self.driver.find_element(By.CSS_SELECTOR, selector)
                        break
                    except:
                        continue

                if container:
                    # Extract text - this didn't work well for most listings though, since bullet points etc are nested HTML elements
                    text_method = container.text.strip()
                    try:
                        # Try to use beautiful soup library to extract the job desc text
                        from bs4 import BeautifulSoup

                        inner_html = container.get_attribute("innerHTML")
                        soup = BeautifulSoup(inner_html, "html.parser")
                        soup_text = soup.get_text(separator="\n", strip=True)

                        # Use whichever extraction method worked better
                        job_data["description"] = (
                            soup_text
                            if len(soup_text) > len(text_method)
                            else text_method
                        )
                    except ImportError:
                        job_data["description"] = text_method
                else:
                    job_data["description"] = "Not Found"

            except Exception as e:
                job_data["description"] = ""
                print(f"Could not extract description: {e}")

        except Exception as e:
            print(f"Error extracting job details from {job_url}: {e}")
        return job_data

    def extract_degree_requirements(self, job_description):
        """
        Find words that indicate the degree requirement for the job
        
        :param self:
        :param job_description: Description extracted from URL
        
        :return: Degree if mentioned in description, otherwise Not Specified
        """
        if not job_description or pd.isna(job_description):
            return "Not Specified"

        job_description_lower = job_description.lower()

        # Regex of degree types
        degree_patterns = [
            (
                r"\bbachelor[\'s]*\b|\bb\.?s\.?c?\.?\b|\bb\.?a\.?\b|\bundergraduate\b",
                "Bachelor's",
            ),
            (r"\bmaster[\'s]*\b|\bm\.?s\.?c?\.?\b|\bmba\b|\bm\.?a\.?\b", "Master's"),
            (r"\bph\.?d\.?\b|\bdoctoral\b|\bdoctorate\b", "PhD"),
        ]
        # Return the degree if a match was found
        for pattern, degree in degree_patterns:
            if re.search(pattern, job_description_lower):
                return degree

        if re.search(r"\bdegree\b", job_description_lower):
            return "Degree (Unspecified)"
        return "Not Specified"

    def extract_years_experience(self, job_description):
        """
        Find words that indicate the years of experience requirement for the job
        
        :param self:
        :param job_description: Description extracted from URL
        
        :return: Years number if mentioned in description, otherwise Not Specified
        """
        if not job_description or pd.isna(job_description):
            return "Not Specified"

        job_description_lower = job_description.lower()

        # # Try to only capture numbers if they 
        # ig_keywords = [
        #     "advantage",
        #     "preferred",
        #     "nice to have",
        #     "plus",
        #     "bonus",
        #     "desirable",
        # ]
        # search_txt = job_description_lower
        # for kw in ig_keywords:
        #     if kw in job_description_lower:
        #         search_txt = job_description_lower.split(kw)[0]
        #         break

        all_yrs = []
        # Regex for 3+ years, 3 + years, 3 years, 3-5 years, minimum of 3 years
        experience_patterns = [
            r"(\d+)\s*\+?\s*(?:years?|yrs?)",
            r"(\d+)\s*[-–—to]+\s*(\d+)\s*(?:years?|yrs?)",
            r"minimum\s*(?:of)?\s*(\d+)\s*(?:years?|yrs?)", 
        ]
        
        # Try to match regex pattern
        for pattern in experience_patterns:
            matches = re.finditer(pattern, job_description_lower)
            for match in matches:
                if len(match.groups())==2:
                    # 3-5 years
                    all_yrs.extend([int(match.group(1)), int(match.group(2))])
                else:
                    all_yrs.append(int(match.group(1)))
        
        # Return the max years specified
        if all_yrs:
            max_yrs = max(all_yrs)
            if max_yrs > 10:    # i mean come on
                return "Not Specified"
            return str(max_yrs) # + ("+" if "+" in job_description_lower else "")
        
        # If entry-level job look for entry-level patterns
        if re.search(r"entry[-\s]level|no experience required|junior", job_description_lower):
            return "0"
        return "Not Specified"

    def scrape_jobs(self, search_term="data scientist", location="Israel", max_jobs=25):
        """
        Main function for the job scraping
        
        :param self: 
        :param search_term: Job title
        :param location: Location to filter by
        :param max_jobs: maximum number of jobs to look for
        
        :return: DataFrame with job details
        """
        print("Starting job scraping...")

        # Get set of job listing URLs
        job_urls = self.search_jobs(search_term, location, max_jobs)
        if not job_urls:
            print("No jobs found.")
            return pd.DataFrame()

        # Process job details with a delay to mimic human behavior in looking into URLs
        all_jobs = []
        for i, url in enumerate(job_urls, 1):
            print(f"[{i}/{len(job_urls)}] Processing job URL: {url}")
            job_details = self.extract_job_details(url)

            job_details["degree"] = self.extract_degree_requirements(
                job_details["description"]
            )
            job_details["experience"] = self.extract_years_experience(
                job_details["description"]
            )

            if job_details["location"]:
                job_details["location"] = (
                    job_details["location"].replace(", Israel", "").strip()
                )

            all_jobs.append(job_details)
            if i < len(job_urls):
                delay = random.uniform(2, 5)
                print(f"Waiting for {delay:.2f} seconds before next job...")
                time.sleep(delay)

        jobs_df = pd.DataFrame(all_jobs)
        print("Job scraping completed.")
        return jobs_df

    def close(self):
        """
        Close Senelium browser
                
        :param self: 
        """
        print("Closing browser...")
        self.driver.quit()
        print("Browser closed.")


def run_job_finder_and_save(output_file="job_listings.csv", max_jobs=25):
    """
    Run the job finder scraper and save/update the CSV file
    
    :param output_file: (str) Path to CSV file
    :param max_jobs: Max jobs to look fot
    """
    job_finder = None
    try:
        # Initialize JobFinder
        job_finder = JobFinder(headless=True)

        new_jobs_df = job_finder.scrape_jobs(
            search_term="data scientist", location="Israel", max_jobs=max_jobs
        )

        if new_jobs_df.empty:
            print("No new jobs found.")
            return

        # DataFrame for CSV file
        csv_df = pd.DataFrame(
            {
                "Job Title": new_jobs_df["title"],
                "Company": new_jobs_df["company"],
                "Location (IL)": new_jobs_df["location"],
                "Required Degree": new_jobs_df["degree"],
                "Required Experience (years)": new_jobs_df["experience"],
                #"Job Description": new_jobs_df["description"],
                "Job URL": new_jobs_df["job_url"],
                "Date Retrieved": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )

        # Add new jobs and don't add duplicates, ensure the path exists
        if os.path.exists(output_file):
            existing_df = pd.read_csv(output_file)
            combined_df = (
                pd.concat([existing_df, csv_df])
                .drop_duplicates(subset=["Job URL"])
                .reset_index(drop=True)
            )
            print(
                f"Appended new jobs to {output_file}. Total jobs now: {len(combined_df)}"
            )
        else:
            combined_df = csv_df
            print(f"Saved new jobs to {output_file}. Total jobs: {len(csv_df)}")

        combined_df.to_csv(output_file, index=False)
        print(f"Saved job listings to {output_file}")
        
        with open('last_run.txt', 'w') as f:
            f.write(datetime.now().isoformat())
        print(f"Updated last_run.txt")
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if job_finder:
            job_finder.close()


if __name__ == "__main__":
    run_job_finder_and_save(output_file="job_listings.csv", max_jobs=50)
