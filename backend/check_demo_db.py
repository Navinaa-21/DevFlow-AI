from app.db.session import SessionLocal
from app.models.workspace import Workspace
from app.models.repository import Repository
from app.models.invitation import Invitation

db = SessionLocal()
try:
    print("--- Database Content Verification ---")
    workspaces = db.query(Workspace).all()
    print(f"Total Workspaces: {len(workspaces)}")
    for w in workspaces:
        print(f"WS ID: {w.id} | Name: {w.name} | Slug: {w.slug}")
        
    repos = db.query(Repository).all()
    print(f"\nTotal Connected Repositories: {len(repos)}")
    for r in repos:
        print(f"Repo ID: {r.id} | Name: {r.name} | Active: {r.is_active}")
        
    invites = db.query(Invitation).all()
    print(f"\nTotal Invitations: {len(invites)}")
    for i in invites:
        print(f"Invite ID: {i.id} | Email: {i.email} | Role: {i.role} | Status: {i.status}")
finally:
    db.close()
