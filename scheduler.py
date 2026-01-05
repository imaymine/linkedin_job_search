from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta
import pytz
from find_jobs import run_job_finder_and_save

class JobFinderScheduler:
    """
    Automatic job scraping every 12/24 hours
    """
    def __init__(self, interval=0.5):
        """
        Initialize scheduler
        
        :param self: 
        :param interval: Interval (hours, int) between job scraping (12/24)
        """
        self.interval = interval
        self.scheduler = BackgroundScheduler(timezone=pytz.timezone('Asia/Jerusalem'))
        self.next_run = None
        
    def find_jobs(self):
        """
        Run job finder and update next run time
        
        :param self:
        """
        print(f"\n{'='*50}")
        print(f"Automatic job-finding started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*50}\n")
        
        run_job_finder_and_save(max_jobs=50)
        
        with open('last_run.txt', 'w') as f:
            f.write(datetime.now().isoformat())
        
        self.next_run = datetime.now() + timedelta(hours=self.interval)
        
        print(f"\n{'='*50}")
        print(f"Next job-finding will begin at {self.next_run.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*50}\n")
        
    def start(self, run_on_init=True):
        """
        Start the scheduler
                
        :param self: 
        :param run_on_init: If true, will run the scraper immediately
        """
        
        self.scheduler.add_job(func=self.find_jobs,
                               trigger=IntervalTrigger(hours=self.interval),
                               id='jobfinder_linkedin',
                               name='JobFinder LinkedIn',
                               replace_existing=True)
        self.scheduler.start()
        print(f"Scheduler has started and will run every {self.interval} hours")
        
        if run_on_init:
            self.find_jobs()
        else:
            self.next_run = datetime.now() + timedelta(hours=self.interval)
            print(f"First run scheduled for {self.next_run.strftime('%Y-%m-%d %H:%M:%S')}")
            
    def stop(self):
        """
        Stop the scheduler
        
        :param self: 
        """
        self.scheduler.shutdown()
        print("Scheduler has stopped.")
        
    def get_time_to_next_run(self):
        """
        Get time in seconds until the next scheduled run
        
        :param self: 
        """
        if self.next_run:
            delta = self.next_run - datetime.now()
            return max(0, int(delta.total_seconds()))
        return 0
    
if __name__ == "__main__":
    # Test
    scheduler = JobFinderScheduler(interval=12)
    scheduler.start(run_on_init=True)
    
    print("\nScheduler is running. Press Ctrl+C to stop.")
    
    try:
        # Keep script running
        import time
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("\nStopping scheduler...")
        scheduler.stop()