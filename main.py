from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.orm import Session

import models
import schemas
import services
from db import engine, get_db

# Create all database tables based on models.py
models.base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Corporate Event Management API",
    description="Acme Corp Internal Event System",
    version="1.0.0",
)

# ---------------------------------------------
# EVENT ENDPOINTS
# ---------------------------------------------


@app.post(
    "/events", response_model=schemas.EventResponse, status_code=status.HTTP_201_CREATED
)
def create_event(event: schemas.EventCreate, db: Session = Depends(get_db)):
    return services.create_event(db=db, event=event)


@app.get("/events", response_model=list[schemas.EventResponse])
def read_events(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return services.get_events(db, skip=skip, limit=limit)


@app.get("/events/{id}", response_model=schemas.EventResponse)
def read_event(id: int, db: Session = Depends(get_db)):
    db_event = services.get_event(db, event_id=id)
    if db_event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )
    return db_event


@app.put("/events/{id}", response_model=schemas.EventResponse)
def update_event(id: int, event: schemas.EventUpdate, db: Session = Depends(get_db)):
    db_event = services.update_event(db, event_id=id, event_update=event)
    if db_event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )
    return db_event


@app.delete("/events/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(id: int, db: Session = Depends(get_db)):
    success = services.delete_event(db, event_id=id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )
