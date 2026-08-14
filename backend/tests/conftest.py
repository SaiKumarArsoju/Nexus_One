from uuid import uuid4

import pytest
from app.core.enums import MachineStatus
from app.database.session import get_db
from app.main import app
from app.models import Factory, Machine, ProductionLine
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

TEST_DATABASE_URL = "postgresql+psycopg://nexus_user:nexus_password@localhost:5432/nexus_one_test"

test_engine = create_engine(
    TEST_DATABASE_URL,
    pool_pre_ping=True,
)

TestingSessionLocal = sessionmaker(
    bind=test_engine,
    autoflush=False,
    autocommit=False,
    class_=Session,
)


def override_get_db():
    database = TestingSessionLocal()

    try:
        yield database
    finally:
        database.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def db() -> Session:
    database = TestingSessionLocal()

    try:
        yield database
    finally:
        database.rollback()
        database.close()


@pytest.fixture
def test_factory(db: Session) -> Factory:
    unique_id = uuid4().hex[:8]

    factory = Factory(
        name=f"Test Factory {unique_id}",
        code=f"TEST_{unique_id}",
        location="Test Location",
    )

    db.add(factory)
    db.commit()
    db.refresh(factory)

    return factory


@pytest.fixture
def test_production_line(
    db: Session,
    test_factory: Factory,
) -> ProductionLine:
    production_line = ProductionLine(
        name="Test Production Line",
        factory_id=test_factory.id,
    )

    db.add(production_line)
    db.commit()
    db.refresh(production_line)

    return production_line


@pytest.fixture
def test_machine(
    db: Session,
    test_production_line: ProductionLine,
) -> Machine:
    unique_id = uuid4().hex[:8]

    machine = Machine(
        name="Test Machine",
        serial_number=f"TEST-MACHINE-{unique_id}",
        manufacturer="NEXUS Test",
        model_number="TEST-001",
        status=MachineStatus.RUNNING,
        production_line_id=test_production_line.id,
    )

    db.add(machine)
    db.commit()
    db.refresh(machine)

    return machine
