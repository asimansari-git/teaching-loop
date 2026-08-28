from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from .. import models, database, auth
from datetime import timedelta
from typing import List

router = APIRouter(
    prefix="/auth",
    tags=["authentication"]
)

@router.get("/organizations", response_model=List[models.OrganizationOut])
def get_organizations(db: Session = Depends(database.get_db)):
    return db.query(models.Organization).all()

@router.post("/register", response_model=models.UserOut)
def register(user: models.UserCreate, db: Session = Depends(database.get_db)):
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # Organization Logic
    org_id = user.organization_id
    
    if user.new_organization_name:
        # Check if teacher (only teachers can create orgs?) -> Requirement says "selection or creation of organization for teachers"
        if user.role != "teacher":
            raise HTTPException(status_code=403, detail="Only teachers can create organizations")
            
        existing_org = db.query(models.Organization).filter(models.Organization.name == user.new_organization_name).first()
        if existing_org:
            raise HTTPException(status_code=400, detail="Organization name already exists")
            
        new_org = models.Organization(name=user.new_organization_name)
        db.add(new_org)
        db.commit()
        db.refresh(new_org)
        org_id = new_org.id
    
    if not org_id:
        raise HTTPException(status_code=400, detail="Organization is required")

    hashed_password = auth.get_password_hash(user.password)
    new_user = models.User(
        username=user.username, 
        hashed_password=hashed_password, 
        role=user.role,
        organization_id=org_id
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/token", response_model=models.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username, "role": user.role, "org_id": user.organization_id, "user_id": user.id}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}
