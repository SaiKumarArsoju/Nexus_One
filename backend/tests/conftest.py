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


@pytest.fixture
def db() -> Session:
    connection = test_engine.connect()
    transaction = connection.begin()

    database = TestingSessionLocal(bind=connection)

    try:
        yield database
    finally:
        database.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db: Session) -> TestClient:
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def test_factory(db: Session) -> Factory:
    factory = Factory(
        name="Test Factory",
        code="TEST_FACTORY",
        location="Test Location",
    )

    db.add(factory)
    db.flush()

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
    db.flush()

    return production_line


@pytest.fixture
def test_machine(
    db: Session,
    test_production_line: ProductionLine,
) -> Machine:
    machine = Machine(
        name="Test Machine",
        serial_number="TEST-MACHINE-001",
        manufacturer="NEXUS Test",
        model_number="TEST-001",
        status=MachineStatus.RUNNING,
        production_line_id=test_production_line.id,
    )

    db.add(machine)
    db.flush()

    return machine
