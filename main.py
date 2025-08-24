"""
Coding CLub: Backend Task 1
Parse the log file and prepare a report
"""
import re
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

# Read logfile data
with open("timetable.log") as f:
    lines = f.readlines()

# Initialise the performance metrics to measure from the data
total_requests = 0
endpoint_counts = {}
response_times = {}
status_code_counts = {}
ip_user_map = {}
user_ids = set()
users_by_year = {}
requests_per_hour = {}
user_request_count = {}
new_user_set = set()

# Timetable generation
generation_strategies = {}
total_timetables_generated = 0
generate_calls = 0
returned_timetables_total = 0
longest_response_time = 0
longest_response_detail = None

# Using Python's regex module, set up regexes to parse through log lines
# Request pattern regex:
# example: 2025/08/01 08:00:23 [103.144.92.199] POST /courses 200 418.024µs
request_pattern = re.compile(
    r"(?P<timestamp>\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}) \[(?P<ip>[\d.]+)] (?P<method>GET|POST) (?P<endpoint>/\S+) ("
    r"?P<status>\d{3}) (?P<response_time>[\d.]+)(?P<unit>ms|µs)"
)

# Router pattern regex:
# example: 2025/08/01 08:00:23 [103.144.92.199] router: /courses [2023A4PS0694P]
router_pattern = re.compile(
    r"\[(?P<ip>[\d.]+)] router: (?P<endpoint>/\S+)(?: \[(?P<user_id>[A-Z0-9]+)])?"
)

# Strategy pattern regex:
# example: 2025/08/01 08:00:29 [106.205.200.150] --- Using Heuristic Backtracking Strategy (for Sparse Spaces) ---
strategy_pattern = re.compile(
    r"Using (?P<strategy>Heuristic Backtracking|Iterative Random Sampling) Strategy"
)

# Generation pattern regex:
# 2025/08/01 08:00:29 [106.205.200.150] --- Generation Complete: Found 234 timetables in pool, returning 100. ---
generation_complete_pattern = re.compile(
    r"Generation Complete: Found (?P<found>\d+) timetables in pool, returning (?P<returned>\d+)\."
)

# Map IPs to users
for line in lines:
    # Check if line matches with router pattern
    match = router_pattern.search(line)

    if match:
        # Data found in the match
        ip = match["ip"]
        endpoint = match["endpoint"]
        user_id = match.group("user_id")

        if user_id:
            ip_user_map[(ip, endpoint)] = user_id

            # Get user year
            year = int(user_id[:4])
            user_ids.add(user_id)

            if year not in users_by_year:
                users_by_year[year] = set()

            users_by_year[year].add(user_id)
            new_user_set.add(user_id)

# Requests data
request_data = []
last_ip = None

for line in lines:
    # Check if line matches with request pattern
    match = request_pattern.search(line)

    if match:
        # Increment requests
        total_requests += 1

        # Data found in the match
        ip = match["ip"]
        endpoint = match["endpoint"]
        response_time = float(match["response_time"])
        status = int(match["status"])
        unit = match["unit"]
        timestamp = datetime.strptime(match["timestamp"], "%Y/%m/%d %H:%M:%S")

        if unit == "µs":
            response_time /= 1000

        # endpoint_counts
        if endpoint not in endpoint_counts:
            endpoint_counts[endpoint] = 0

        endpoint_counts[endpoint] += 1

        # response_times
        if endpoint not in response_times:
            response_times[endpoint] = []
        response_times[endpoint].append(response_time)

        # status_code_counts
        if status not in status_code_counts:
            status_code_counts[status] = 0
        status_code_counts[status] += 1

        # requests_per_hour
        hour_key = timestamp.strftime("%Y-%m-%d %H:00")
        if hour_key not in requests_per_hour:
            requests_per_hour[hour_key] = 0
        requests_per_hour[hour_key] += 1

        request_data.append(
            {
                "timestamp": timestamp,
                "hour": timestamp.strftime("%H"),
                "endpoint": endpoint,
                "status": status,
                "response_time_ms": response_time,
            }
        )

        # Check if this response time was the longest
        if response_time > longest_response_time:
            longest_response_time = response_time
            longest_response_detail = (
                f"{endpoint} at {timestamp} ({response_time:.3f}ms)"
            )

        if endpoint == "/generate":
            generate_calls += 1
            last_ip = ip
        else:
            last_ip = None

        user_id = ip_user_map.get((ip, endpoint))
        if user_id:
            if user_id not in user_request_count:
                user_request_count[user_id] = 0
            user_request_count[user_id] += 1
            new_user_set.discard(user_id)

    # Checks if line matches with strategy pattern
    strategy_match = strategy_pattern.search(line)
    if strategy_match:
        if last_ip and f"[{last_ip}]" in line:
            strategy = strategy_match["strategy"]

            if strategy not in generation_strategies:
                generation_strategies[strategy] = 0
            generation_strategies[strategy] += 1

    # Checks if line matches with generation pattern
    gen_match = generation_complete_pattern.search(line)

    if gen_match:
        if last_ip and f"[{last_ip}]" in line:
            found = int(gen_match["found"])
            returned = int(gen_match["returned"])

            total_timetables_generated += found
            returned_timetables_total += returned

# Build DataFrame
df_requests = pd.DataFrame(request_data)

# Print report
print("\nAPI METRICS")
print(f"Total API Requests: {total_requests}")
print("\nEndpoint Popularity")
for ep, count in endpoint_counts.items():
    print(f"{ep}: {count} requests")

print("\nPerformance Metrics (avg, max in ms)")
for ep, times in response_times.items():
    print(f"{ep}: avg={sum(times)/len(times):.2f}, max={max(times):.2f}")

print(f"\nLongest Single Response: {longest_response_detail}")

print("\nHTTP Status Codes")
for code, count in status_code_counts.items():
    print(f"{code}: {count} responses")

print("\nUnique Users")
print(f"Total Unique Users: {len(user_ids)}")
for year, users in users_by_year.items():
    print(f"{year}: {len(users)} users")

print("\nTimetable Generation")
print(f"Total /generate Calls: {generate_calls}")
print(f"Total Timetables Generated: {total_timetables_generated}")
print(f"Total Timetables Returned: {returned_timetables_total}")

if generate_calls:
    print(
        f"Avg Timetables Generated per /generate: {total_timetables_generated / generate_calls:.2f}"
    )
    print(
        f"Avg Timetables Returned per /generate: {returned_timetables_total / generate_calls:.2f}"
    )

print("\nStrategy Usage")
for strat, count in generation_strategies.items():
    print(f"{strat}: {count} times")

# Visualisations, using matplotlib and seaborn
sns.color_palette("Blues", as_cmap=True)

# Endpoint Popularity bar graph
plt.figure(figsize=(10, 6))
sns.barplot(
    x=list(endpoint_counts.keys()),
    y=list(endpoint_counts.values()),
    hue=list(endpoint_counts.keys()),
    palette="Blues",
    legend=False,
)
plt.title("Endpoint Popularity")
plt.xlabel("Endpoint")
plt.ylabel("Request Count")
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()

# Requests by hour of day bar graph
plt.figure(figsize=(10, 6))
sns.countplot(
    data=df_requests,
    x="hour",
    hue="hour",
    order=sorted(df_requests["hour"].unique()),
    palette="Blues",
    legend=False,
)
plt.title("Requests by Hour of Day")
plt.xlabel("Hour")
plt.ylabel("Request Count")
plt.tight_layout()
plt.show()

# Status Code Pie Chart
plt.figure(figsize=(6, 6))

num_slices = len(status_code_counts)
colors = sns.color_palette("Blues", num_slices)
plt.pie(
    status_code_counts.values(),
    startangle=140,
    colors=colors,
)

plt.legend(status_code_counts.keys(), loc='best')
plt.title("HTTP Status Code Distribution")
plt.tight_layout()
plt.show()

# Timetable Generation Strategy
plt.figure(figsize=(6, 5))
sns.barplot(
    x=list(generation_strategies.keys()),
    y=list(generation_strategies.values()),
    hue=list(generation_strategies.keys()),
    palette="Blues",
    legend=False,
)
plt.title("Timetable Generation Strategy Usage")
plt.ylabel("Count")
plt.tight_layout()
plt.show()

# Heatmap of Requests by Hour and Endpoint
heatmap_data = df_requests.groupby(["hour", "endpoint"]).size().unstack(fill_value=0)
plt.figure(figsize=(12, 6))
sns.heatmap(heatmap_data, cmap="Blues", annot=True, fmt="d")
plt.title("Heatmap of Requests by Endpoint and Hour")
plt.xlabel("Endpoint")
plt.ylabel("Hour")
plt.tight_layout()
plt.show()
