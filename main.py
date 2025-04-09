from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import cliente, proveedor, producto


app = FastAPI(title="API de Mundo Friki")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(cliente.router, prefix="/cliente", tags=["Cliente"])

@app.get("/")
def root():
    return {"mensaje": "Bienvenido a la API de Mundo Friki"}

app.include_router(proveedor.router, tags=["Proveedores"])
app.include_router(producto.router, prefix="/comics", tags=["Cómics"])

origins = [
    "http://localhost:5000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

