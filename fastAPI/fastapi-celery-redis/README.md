# Python FastAPI with celery and Redis with full DevSecops practice


## TODO
- [ ] Sarif files are not accepted by sonar scan



```sh
poetry new .
eval $(poetry env activate)
poetry lock
poetry install --no-root
```

```sh
docker-compose up --built
```

```sh
docker-compose up sonar-scanner
# it will first start the trivvy scan then sonar
```