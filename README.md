# nexus-fleet-service

Vehicle and fleet-logistics endpoints. Part of the polyrepo split — see
`nexus-infra` for the overall repo map.

**Verifies tokens statelessly** — `JWT_SECRET_KEY` here must equal
`nexus-identity-service`'s value. This service never calls identity-service
per request; it only shares its token-signing secret.

## Run locally

```
cp .env.example .env      # JWT_SECRET_KEY must match nexus-identity-service
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8004
```

## Test

```
pytest
```
