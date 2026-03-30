from fastapi import FastAPI

app = FastAPI(title='Creator Analytics API')


@app.get('/health')
def health() -> dict[str, str]:
    return {'status': 'ok'}

