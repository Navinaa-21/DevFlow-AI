import pytest
from app.db.session import SessionLocal, engine

@pytest.fixture
def db_session():
    """
    Fixture that provides a database session bound to a transaction.
    The transaction is rolled back after the test completes.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = SessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()
