# Demo Script

1. Start the platform:

```bash
docker compose up --build -d
```

2. Check gateway and services:

```bash
curl http://localhost:8480/health
curl http://localhost:8480/services/health
```

3. Run booking workflow demo:

```bash
python scripts/demo_pipeline.py
```

4. Open frontend dashboard:

- `http://localhost:5177`
- use `HOST-001` in dashboard input

5. Validate tests:

```bash
python -m pytest -q
```
