from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal
from models.cliente import Cliente
from schemas.cliente import ClienteCreate, ClienteOut, ClienteLogin  
from passlib.context import CryptContext
from models.compra import Compra, ItemCompra  
from typing import List
from pydantic import BaseModel

from datetime import datetime  
from models.producto import Comic 
from models.compra import Compra, ItemCompra  


router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Dependencia de DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/login")
def login_cliente(data: ClienteLogin, db: Session = Depends(get_db)):
    cliente = db.query(Cliente).filter(Cliente.correo == data.correo).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Correo no encontrado")

    if not pwd_context.verify(data.password, cliente.password):
        raise HTTPException(status_code=401, detail="Contraseña incorrecta")

    return {
        "mensaje": "Inicio de sesión exitoso",
        "cliente_id": cliente.id_cliente,
        "nombre": cliente.nombre,
        "correo": cliente.correo,
        "rol": cliente.rol
    }


@router.post("/", response_model=ClienteOut)
def crear_cliente(cliente: ClienteCreate, db: Session = Depends(get_db)):
    hashed_password = pwd_context.hash(cliente.password)

    hashed_password = pwd_context.hash(cliente.password)
    nuevo_cliente = Cliente(
        nombre=cliente.nombre,
        correo=cliente.correo,
        telefono=cliente.telefono,
        membresia=cliente.membresia,
        password=hashed_password,
    )
    db.add(nuevo_cliente)
    db.commit()
    db.refresh(nuevo_cliente)
    return nuevo_cliente

@router.get("/", response_model=list[ClienteOut])
def listar_clientes(db: Session = Depends(get_db)):
    return db.query(Cliente).all()





class ItemPedido(BaseModel):
    comic_id: int
    cantidad: int

class PedidoCreate(BaseModel):
    items: List[ItemPedido]

@router.post("/pedido")
def crear_pedido(
    pedido: PedidoCreate,
    cliente_id: int,  
    db: Session = Depends(get_db)
):

    cliente = db.query(Cliente).get(cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")


    total = 0.0
    detalles = []
    
    for item in pedido.items:
        comic = db.query(Comic).get(item.comic_id)
        if not comic:
            raise HTTPException(status_code=404, detail=f"Cómic ID {item.comic_id} no existe")
        
        if comic.stock < item.cantidad:
            raise HTTPException(
                status_code=400,
                detail=f"Stock insuficiente para '{comic.nombre}'. Disponible: {comic.stock}"
            )
        
     
        precio = comic.precio_oferta if comic.precio_oferta else comic.precio
        subtotal = precio * item.cantidad
        total += subtotal
        
        detalles.append({
            "comic_id": comic.id_comic,
            "nombre": comic.nombre,
            "cantidad": item.cantidad,
            "precio_unitario": precio,
            "subtotal": subtotal
        })

    return {
        "cliente_id": cliente_id,
        "cliente_nombre": cliente.nombre,
        "items": detalles,
        "total": total,
        "mensaje": "Pedido válido. Usa /comprar para confirmar."
    }

@router.post("/comprar")
def confirmar_compra(
    pedido: PedidoCreate,
    cliente_id: int,
    db: Session = Depends(get_db)
):
    # Verificar cliente
    cliente = db.query(Cliente).get(cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    # Crear registro de compra
    nueva_compra = Compra(
        cliente_id=cliente_id,
        fecha_compra=datetime.now(),  # ¡Ahora datetime está importado!
        total=0.0,
        estado="completada"
    )
    db.add(nueva_compra)
    db.flush()

    # Procesar items
    total = 0.0
    for item in pedido.items:
        comic = db.query(Comic).get(item.comic_id)  # ¡Ahora Comic está importado!
        if not comic or comic.stock < item.cantidad:
            db.rollback()
            raise HTTPException(
                status_code=400,
                detail=f"Error con el cómic ID {item.comic_id}"
            )

        precio = comic.precio_oferta if comic.precio_oferta else comic.precio
        subtotal = precio * item.cantidad
        total += subtotal

        # Registrar item
        db.add(ItemCompra(
            compra_id=nueva_compra.id_compra,
            producto_id=comic.id_producto,
            cantidad=item.cantidad,
            precio_unitario=precio,
            subtotal=subtotal
        ))

        # Actualizar stock
        comic.stock -= item.cantidad

    nueva_compra.total = total
    db.commit()

    return {"mensaje": "Compra exitosa", "compra_id": nueva_compra.id_compra}