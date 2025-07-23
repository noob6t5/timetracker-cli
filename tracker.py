import argparse
import json
import os
import time
import subprocess
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

DB_PATH = "grind_tracker.json"       # Repo-rooted DB file
REPORT_PATH = "grind_report.png"
SUMMARY_PATH = "grind_summary.md"
README_PATH = "README.md"

def load_db():
    if not os.path.exists(DB_PATH):
        return {}
    with open(DB_PATH, 'r') as f:
        return json.load(f)

def save_db(data):
    with open(DB_PATH, 'w') as f:
        json.dump(data, f, indent=2)

def git_commit_push(files, message):
    try:
        subprocess.run(["git", "add"] + files, check=True)
        subprocess.run(["git", "commit", "-m", message], check=True)
        subprocess.run(["git", "push"], check=True)
        print("[+] Changes pushed to GitHub.")
    except subprocess.CalledProcessError as e:
        print(f"[-] Git command failed: {e}")

def start_timer(category):
    db = load_db()
    if "active" in db:
        print("[-] Timer already running. Stop it first.")
        return
    db["active"] = {"category": category, "start": time.time()}
    save_db(db)
    print(f"[+] Started '{category}' session.")

def stop_timer():
    db = load_db()
    if "active" not in db:
        print("[-] No active timer running.")
        return
    session = db.pop("active")
    end_time = time.time()
    duration = end_time - session["start"]
    date_str = datetime.now().strftime('%Y-%m-%d')
    category = session["category"]

    if date_str not in db:
        db[date_str] = {}
    db[date_str][category] = db[date_str].get(category, 0) + duration
    save_db(db)

    print(f"[+] Stopped session. Logged {duration/3600:.2f} hrs to '{category}'.")

    generate_report()
    # Commit and push DB, report, summary, README
    git_commit_push(
        [DB_PATH, REPORT_PATH, SUMMARY_PATH, README_PATH],
        f"Auto-update: Logged {duration/3600:.2f} hrs to {category} on {date_str}"
    )

def generate_report():
    db = load_db()
    end = datetime.now()
    start = end - timedelta(days=7)
    totals = {}
    daily_logs = {}

    for date_str, data in db.items():
        if date_str == "active":
            continue
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        except:
            continue
        if not (start <= date_obj <= end):
            continue
        for cat, secs in data.items():
            totals[cat] = totals.get(cat, 0) + secs
            if date_str not in daily_logs:
                daily_logs[date_str] = {}
            daily_logs[date_str][cat] = daily_logs[date_str].get(cat, 0) + secs

    if not totals:
        print("[-] No data to generate report.")
        return

    hours = {k: round(v / 3600, 2) for k, v in totals.items()}

    plt.figure(figsize=(6,6))
    plt.pie(hours.values(), labels=hours.keys(), autopct='%1.1f%%')
    plt.title("Weekly Grind Breakdown")
    plt.savefig(REPORT_PATH)
    plt.close()
    print(f"[+] Pie chart saved to '{REPORT_PATH}'")

    md_table = "| Category  | Time Spent (hrs) |\n|-----------|------------------|\n"
    for cat, h in sorted(hours.items(), key=lambda x: -x[1]):
        md_table += f"| {cat:<9}| {h:>6} hrs        |\n"

    daily_section = "\n## 📅 Daily Logs (Past 7 Days)\n\n"
    for day in sorted(daily_logs.keys(), reverse=True):
        daily_section += f"### {day}\n\n"
        daily_section += "| Category  | Time Spent (hrs) |\n|-----------|------------------|\n"
        for cat, secs in daily_logs[day].items():
            h = round(secs / 3600, 2)
            daily_section += f"| {cat:<9}| {h:>6} hrs        |\n"
        daily_section += "\n"

    summary_content = (
        "## 🧠 Weekly Grind Time Breakdown\n\n"
        f"![Grind Chart](./{REPORT_PATH})\n\n"
        + md_table
        + daily_section
    )

    with open(SUMMARY_PATH, "w") as f:
        f.write(summary_content)

    with open(README_PATH, "w") as f:
        f.write(summary_content)

    print("[+] Markdown summary written to README.md and grind_summary.md")

def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")

    p_start = subparsers.add_parser("start")
    p_start.add_argument("category")

    subparsers.add_parser("stop")
    subparsers.add_parser("report")

    args = parser.parse_args()

    if args.command == "start":
        start_timer(args.category)
    elif args.command == "stop":
        stop_timer()
    elif args.command == "report":
        generate_report()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

