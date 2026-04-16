# Tracker LM Agent

Python scripts for working with Yandex Tracker API and generating analytical outputs via local LLM tools.

## Setup

1. Create and activate virtual environment:
   - `python3 -m venv venv`
   - `source venv/bin/activate`
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Create `.env` file:

```env
TRACKER_TOKEN=your_oauth_token
# For Yandex 360:
TRACKER_ORG_ID=your_org_id
# Or for Yandex Cloud:
# TRACKER_CLOUD_ORG_ID=your_cloud_org_id
```

## Main Scripts

- `fetch_goal_full.py` - full goal dump (details, comments, relations, attachments, changelog).
- `fetch_project_full.py` - full project dump (v2/v3 data, comments, relations, queues, attachments).
- `fetch_issue_full.py` - full issue dump (issue, comments, links, transitions, changelog, attachments).

## Usage

```bash
python3 fetch_goal_full.py --goal 3744
python3 fetch_project_full.py --project 2465
python3 fetch_issue_full.py --issue SVT-123
```

Optional output file:

```bash
python3 fetch_goal_full.py --goal 3744 --output goal_3744_dump.json
```

## Notes

- Scripts use "best effort" requests: if one endpoint is unavailable, remaining calls still run.
- Runtime JSON/Markdown artifacts are ignored by git to keep the repository clean.
