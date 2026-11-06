FOOTBALL LIVE DATA BRIDGE
========================

Purpose
-------
This small FastAPI service connects ChatGPT (through a Custom GPT Action or
another OpenAPI-compatible client) to API-Football.

Files
-----
app.py          Main API bridge
requirements.txt Python dependencies
render.yaml    Render deployment configuration
openapi.yaml   OpenAPI schema for the ChatGPT Action
README.txt     These instructions

IMPORTANT SECURITY
------------------
1. Never put your API-Football key in GitHub or inside app.py.
2. Keep this GitHub repository free of secrets.
3. Set API_FOOTBALL_KEY only as a secret environment variable in Render.
4. Render generates BRIDGE_API_KEY. Keep that value private.
5. Do not share either key in chat or screenshots.

Deploy on Render
----------------
1. Upload all files in this ZIP to your GitHub repository.
2. In Render, choose New + > Web Service and connect this repository.
3. Use the settings from render.yaml (Python runtime).
4. Add API_FOOTBALL_KEY in the Render environment variables using your
   current API-Football key. Do not add it to GitHub.
5. Keep the generated BRIDGE_API_KEY private.
6. Deploy and wait for the service to become live.
7. Open https://YOUR-SERVICE.onrender.com/health to check the service.
8. Replace the placeholder server URL in openapi.yaml with your real Render URL.

ChatGPT connection
------------------
When the bridge is deployed, create or configure a Custom GPT Action and
import openapi.yaml. The Action must send the x-bridge-key header using
your private BRIDGE_API_KEY.

Limitations
-----------
- This is an initial bridge, not a production-grade betting system.
- The free API-Football plan has request limits. Avoid frequent polling.
- Live odds and bookmaker coverage depend on your API-Football subscription
  and the data available for each match. Napoleon Sports coverage is not
  guaranteed.
- The service has not been deployed or live-tested in your account yet.
- Render free services may sleep when inactive and take time to wake up.
