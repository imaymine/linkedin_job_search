from flask import Flask, render_template_string, send_file, jsonify
import pandas as pd
import os
from datetime import datetime, timedelta
from scheduler import JobFinderScheduler

app = Flask(__name__)

scheduler = JobFinderScheduler(interval=12)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Job Listings from LinkedIn</title>
    <style>
        body {
            font-family: Tahoma, sans-serif;
            margin: 0 auto;
            background-color: #f4f4f4;
        }
        h1 {
            color: #181899;
            text-align: center;
        }
        .info_box {
            background: white;
            padding: 10px;
            margin: 10px auto;
            width: 50%;
            border-radius: 8px;
        }
        .info_box p {
            margin: 5px 0;
        }
        .info_box p:first-child {
            margin-top: 0;
        }
        .download_button {
            background-color: #2f2fa3;
            color: white;
            padding: 10px 20px;
            text-decoration: none;
            border-radius: 5px;
            display: inline-block;
        }
        .download_button:hover {
            background-color: #181899;
        }
        table {
            width: 85%;
            margin: 20px auto;
            border-collapse: collapse;
        }
        th {
            background-color: #181899;
            color: white;
            padding: 10px;
            border: 1px solid #ddd;
        }
        td {
            padding: 10px;
            border: 1px solid #ddd;
        }
        tr:hover {
            background-color: #f1f1f1;
        }
    </style>
</head>
<body>
    <h1>Job Listings from LinkedIn</h1>
    <div class="info_box">
        <p><strong>Total Jobs Found:</strong> {{ total_jobs }}</p>
        <p><strong>Companies:</strong> {{ unique_companies }}</p>
        <p><strong>Last Updated:</strong> {{ last_update }}</p>
        <p><strong>Next Update:</strong> <span id="next_update_time">{{ next_run_time }}</span></p>
        <p><strong>Countdown to next update:</strong> <span id="countdown">Loading...</span></p>
        <div style="text-align: center; margin-top: 10px;">
            <a class="download_button" href="/download">Download CSV</a>
        </div>
    </div>
    {% if jobs|length > 0 %}
    <table>
        <tr>
            <th>Job Title</th>
            <th>Company</th>
            <th>Location</th>
            <th>Degree</th>
            <th>Experience</th>
            <th>Link</th>
            <th>Date Retrieved</th>
        </tr>
        {% for job in jobs %}
        <tr>
            <td>{{ job['Job Title'] }}</td>
            <td>{{ job['Company'] }}</td>
            <td>{{ job['Location (IL)'] }}</td>
            <td>{{ job['Required Degree'] }}</td>
            <td>{{ job['Required Experience (years)'] }}</td>
            <td><a href="{{ job['Job URL'] }}" target="_blank">View Job</a></td>
            <td>{{ job['Date Retrieved'] }}</td>
        </tr>
        {% endfor %}
    </table>
    {% else %}
    <p style="text-align: center;">No job listings available.</p>
    {% endif %}
    
    <script>
    function updateCountdown() {
        fetch('/api/next_run')
            .then(response => response.json())
            .then(data => {
                let seconds = data.seconds_to_next_run;
                
                if (seconds <= 0) {
                    document.getElementById('countdown').textContent = 'Running now...';
                    // Refresh page every 30 seconds to check for new data
                    setTimeout(() => location.reload(), 30000);
                    return;
                }
                
                // update countdown
                let hours = Math.floor(seconds / 3600);
                let minutes = Math.floor((seconds % 3600) / 60);
                let secs = seconds % 60;
                
                let time = hours + "h " + minutes + "m " + secs + "s";
                document.getElementById('countdown').textContent = time;
            })
            .catch(error => {
                console.error('Error fetching countdown:', error);
                document.getElementById('countdown').textContent = 'Error';
            });
    }
    
    setInterval(updateCountdown, 1000);
    updateCountdown();
</script>
</body>
</html>
"""


@app.route("/")
def index():
    """
    Display job listings and stats
    """
    csv_file = "job_listings.csv"
    last_run_file = "last_run.txt"

    if os.path.exists(csv_file):
        df = pd.read_csv(csv_file)
        jobs = df.to_dict(orient="records")
        total_jobs = len(df)
        unique_companies = df["Company"].nunique()

        if "Date Retrieved" in df.columns and len(df) > 0:
            csv_last_update = pd.to_datetime(df["Date Retrieved"]).max().strftime("%Y-%m-%d %H:%M:%S")
        else:
            csv_last_update = "N/A"
    else:
        jobs = []
        total_jobs = 0
        unique_companies = 0
        csv_last_update = "N/A"
    
    # Check for last run time (even if no new jobs were found)
    if os.path.exists(last_run_file):
        with open(last_run_file, 'r') as f:
            last_run_str = f.read().strip()
            last_run_dt = datetime.fromisoformat(last_run_str)
            last_update = last_run_dt.strftime("%Y-%m-%d %H:%M:%S")
            
            # Calculate next run based on actual last run
            next_run_actual = last_run_dt + timedelta(hours=scheduler.interval)
            next_run_time = next_run_actual.strftime("%Y-%m-%d %H:%M:%S")
    else:
        # use if last_run.txt doesn't exist
        last_update = csv_last_update
        
        # Calculate next run from CSV if available
        if csv_last_update != "N/A":
            last_update_dt = datetime.strptime(csv_last_update, "%Y-%m-%d %H:%M:%S")
            next_run_actual = last_update_dt + timedelta(hours=scheduler.interval)
            next_run_time = next_run_actual.strftime("%Y-%m-%d %H:%M:%S")
        else:
            next_run_time = "N/A"

    return render_template_string(
        HTML_TEMPLATE,
        jobs=jobs,
        total_jobs=total_jobs,
        unique_companies=unique_companies,
        last_update=last_update,
        next_run_time=next_run_time,
    )


@app.route("/download")
def download_csv():
    """
    Download the CSV file
    """
    csv_file = "job_listings.csv"
    if os.path.exists(csv_file):
        return send_file(
            csv_file,
            mimetype="text/csv",
            as_attachment=True,
            download_name=f"job_listings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        )
    else:
        return "CSV file not found.", 404


@app.route("/api/next_run")
def api_next_run():
    """
    Return time to next run in seconds
    """
    last_run_file = "last_run.txt"
    csv_file = "job_listings.csv"
    
    # Try to get last run from file first (most accurate)
    if os.path.exists(last_run_file):
        with open(last_run_file, 'r') as f:
            last_run_str = f.read().strip()
            last_update_dt = datetime.fromisoformat(last_run_str)
    # use CSV if file doesn't exist
    elif os.path.exists(csv_file):
        df = pd.read_csv(csv_file)
        if "Date Retrieved" in df.columns and len(df) > 0:
            last_update_dt = pd.to_datetime(df["Date Retrieved"]).max()
        else:
            return jsonify({"seconds_to_next_run": 0})
    else:
        return jsonify({"seconds_to_next_run": 0})
    
    # Calculate next run
    next_run_actual = last_update_dt + timedelta(hours=scheduler.interval)
    time_until = next_run_actual - datetime.now()
    seconds = int(time_until.total_seconds())
    
    return jsonify({"seconds_to_next_run": seconds})


def start_server(port=5000):
    """
    Start the Flask web server
    """
    csv_file = "job_listings.csv"
    run_rn = not os.path.exists(csv_file)
    last_run_file = "last_run.txt"
    run_rn = False
    if not os.path.exists(csv_file):
        run_rn = True
    elif not os.path.exists(last_run_file):
        run_rn = True
    else:
        with open(last_run_file, 'r') as f:
            last_run_str = f.read().strip()
            last_run_dt = datetime.fromisoformat(last_run_str)
            time_since = datetime.now() - last_run_dt
            if time_since.total_seconds() > (scheduler.interval * 3600):
                run_rn = True
    scheduler.start(run_on_init=run_rn)
    # scheduler.start(run_on_init=True)
    try:
        app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
    finally:
        print("\nShutting down scheduler...")
        scheduler.stop()


if __name__ == "__main__":
    start_server(port=5000)