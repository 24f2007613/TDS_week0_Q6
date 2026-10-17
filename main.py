import yaml
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS: lets the grader's web page call your API from the browser
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Layer 1: defaults ----------
DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}

# ---------- Layer 2: config.development.yaml ----------
YAML_TEXT = """
workers: 6
"""

# ---------- Layer 3: .env file ----------
ENV_FILE_TEXT = """
APP_API_KEY=key-7nbh42ur3z
"""

# ---------- Layer 4: OS env vars (APP_* prefix) ----------
OS_ENV = {
    "APP_WORKERS": "1",
}

ALIASES = {"NUM_WORKERS": "workers"}


def normalize_key(name: str) -> str:
    """NUM_WORKERS -> workers, APP_LOG_LEVEL -> log_level"""
    name = name.strip()
    if name in ALIASES:
        return ALIASES[name]
    if name.startswith("APP_"):
        name = name[4:]
    return name.lower()


def parse_env_text(text: str) -> dict:
    result = {}
    for line in text.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        result[normalize_key(k)] = v.strip().strip('"').strip("'")
    return result


def coerce(key: str, value):
    if key in ("port", "workers"):
        return int(value)
    if key == "debug":
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in ("true", "1", "yes", "on")
    return str(value)


@app.get("/effective-config")
def effective_config(overrides: list[str] = Query(default=[], alias="set")):
    config = dict(DEFAULTS)                                   # 1. defaults
    config.update(yaml.safe_load(YAML_TEXT) or {})            # 2. yaml
    config.update(parse_env_text(ENV_FILE_TEXT))              # 3. .env
    config.update({normalize_key(k): v                        # 4. OS env
                   for k, v in OS_ENV.items()
                   if k.startswith("APP_")})

    # 5. CLI overrides (highest precedence): ?set=port=9000&set=debug=true
    for item in overrides:
        if "=" in item:
            k, v = item.split("=", 1)
            if k.strip():
                config[normalize_key(k)] = v.strip()

    # Convert types
    for k in list(config):
        try:
            config[k] = coerce(k, config[k])
        except (ValueError, TypeError):
            config[k] = DEFAULTS.get(k, config[k])  # ignore bad numbers

    config["api_key"] = "****"                                # mask the secret
    return config
