# clipsmachine

Automated YouTube clips generator + uploader.

## Requirements

- Python 3.10+
- ffmpeg installed and on PATH
- Google Cloud project with YouTube Data API v3 enabled
- OAuth client secrets JSON saved as `client_secret.json` in project root
- OPENAI_API_KEY environment variable set

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .

export OPENAI_API_KEY="sk-..."  # set your key
# place client_secret.json in this directory

clipsmachine run "https://www.youtube.com/watch?v=VIDEO_ID" --privacy public
```
