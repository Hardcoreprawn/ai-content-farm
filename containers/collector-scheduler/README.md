Collector Scheduler

Lightweight scheduler that periodically POSTs to the `content-collector` `/collect` endpoint.

Run once for testing:

```bash
python main.py --once
```

Run as a service (interval seconds configurable):

```bash
SCHEDULE_SECONDS=1800 python main.py
```
