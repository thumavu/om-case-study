Run locally without Docker from the `express-app` folder:

```bash
cd express-app
npm install
npm start
```

Then open:

```text
http://localhost:4567
```

Build and run as a Docker image from the repo root:

```bash
docker build -t express-app ./express-app
docker run --rm -p 4567:4567 express-app
```

Run with Docker Compose from the repo root:

```bash
docker compose -f express-app/compose.yaml up --build
```

Stop the Docker Compose app:

```bash
docker compose -f express-app/compose.yaml down
```
