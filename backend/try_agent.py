from app.agent import run_agent

profile = open("sample/profile.md", encoding="utf-8").read()
job = open("sample/job.txt", encoding="utf-8").read()

for event in run_agent(profile, job):
    if event["step"] == "result":
        print("\n=== FINAL RESUME ===\n")
        print(event["resume"])
        print("\n=== FLAGS (unsupported claims) ===")
        print(event["flags"])
    else:
        print(event["step"], event["status"])
        if "data" in event:
            print(json.dumps(event["data"], indent=2)) if False else print(event["data"])