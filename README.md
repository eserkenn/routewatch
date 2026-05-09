# routewatch

Lightweight HTTP route monitoring daemon that tracks latency regressions and sends alerts via webhooks.

---

## Installation

```bash
pip install routewatch
```

Or install from source:

```bash
git clone https://github.com/yourname/routewatch.git && cd routewatch && pip install .
```

---

## Usage

Define your routes in a `routewatch.yaml` config file:

```yaml
interval: 30
alert_webhook: "https://hooks.slack.com/services/your/webhook/url"
threshold_ms: 500

routes:
  - name: homepage
    url: https://example.com/
  - name: api-health
    url: https://example.com/api/health
    threshold_ms: 200
```

Then start the daemon:

```bash
routewatch start --config routewatch.yaml
```

routewatch will poll each route at the defined interval and fire a webhook alert whenever a route's latency exceeds its threshold or becomes unreachable.

**Example alert payload:**

```json
{
  "route": "api-health",
  "url": "https://example.com/api/health",
  "latency_ms": 843,
  "threshold_ms": 200,
  "status": "regression"
}
```

---

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--config` | `routewatch.yaml` | Path to config file |
| `--verbose` | `false` | Enable detailed logging |
| `--dry-run` | `false` | Poll routes without sending alerts |

---

## License

MIT © 2024 yourname