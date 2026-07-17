from app.db.session import engine
from sqlalchemy import text, inspect

insp = inspect(engine)

print("=== commits table columns ===")
for col in insp.get_columns("commits"):
    nullable = col["nullable"]
    default = col.get("column_default", "")
    print(f"  {col['name']:<30s} {str(col['type']):<30s} nullable={nullable}  default={default}")

print()
print("=== commits table indexes ===")
for idx in insp.get_indexes("commits"):
    print(f"  {idx['name']:<50s} unique={idx['unique']} cols={idx['column_names']}")

print()
print("=== commits table unique constraints ===")
for uc in insp.get_unique_constraints("commits"):
    print(f"  {uc['name']:<50s} cols={uc['column_names']}")

print()
print("=== commits table foreign keys ===")
for fk in insp.get_foreign_keys("commits"):
    print(f"  {fk['name']} -> {fk['referred_table']}.{fk['referred_columns']} ondelete={fk.get('options', {}).get('ondelete')}")

print()
print("=== webhook_events new columns ===")
for col in insp.get_columns("webhook_events"):
    if col["name"] in ("processing_status", "processed_at", "error_message"):
        print(f"  {col['name']:<30s} {str(col['type']):<30s} nullable={col['nullable']}")

print()
print("=== All tables in database ===")
print(" ", sorted(insp.get_table_names()))

print()
print("=== Alembic current revision ===")
with engine.connect() as conn:
    rev = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
    print(f"  {rev}")
