# Local paper-trading deployment

1. Start Moomoo OpenD and log in. Keep paper trading selected.
2. Open PowerShell in this folder:

   `C:\Users\G2\OneDrive\Documents\Ai_Finance_Syariah\backend`

3. Install dependencies:

   `python -m pip install -r requirements.txt`

4. Start the local API:

   `python -m uvicorn local_api:app --host 127.0.0.1 --port 8000`

5. Check the API in a browser:

   - `http://127.0.0.1:8000/health`
   - `http://127.0.0.1:8000/paper/status`
   - `http://127.0.0.1:8000/moomoo/status`
   - `http://127.0.0.1:8000/agent/evaluate` (POST from dashboard)
   - `http://127.0.0.1:8000/approvals`
   - `http://127.0.0.1:8000/audit`

6. Open the local dashboard:

   `..\dashboard\index.html`

7. Run the API smoke test:

   `python test_local_api_smoke.py`

8. Verify quant-agent market data:

   `python check_market_data.py AAPL --strict`

9. Verify Moomoo OpenD paper account status:

   `python check_moomoo_status.py`

The SQLite file `paper_trading.db` is created in this folder. The API is bound to localhost, approval is required, and live trading is disabled.

The local multi-agent path is deterministic at this stage: Shariah agent, quant agent, and risk engine run before the approval queue. No LLM is required for the current workflow.
