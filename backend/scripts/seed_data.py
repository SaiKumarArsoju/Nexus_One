from datetime import date

from app.core.enums import MachineStatus, SensorType
from app.database.session import SessionLocal
from app.models import Factory, Machine, ProductionLine, Sensor
from sqlalchemy import delete

FACTORIES = [
    {
        "name": "Dallas Manufacturing Plant",
        "code": "DAL",
        "location": "Dallas, Texas",
    },
    {
        "name": "Chicago Manufacturing Plant",
        "code": "CHI",
        "location": "Chicago, Illinois",
    },
    {
        "name": "Atlanta Manufacturing Plant",
        "code": "ATL",
        "location": "Atlanta, Georgia",
    },
]
PRODUCTION_LINES = [
    "Engine Assembly",
    "Precision Machining",
    "Paint and Coating",
    "Final Assembly",
]
PRODUCTION_LINES = [
    "Engine Assembly",
    "Precision Machining",
    "Paint and Coating",
    "Final Assembly",
]
SENSOR_CONFIG = [
    ("Temperature Sensor", SensorType.TEMPERATURE, "°C"),
    ("Pressure Sensor", SensorType.PRESSURE, "bar"),
    ("Vibration Sensor", SensorType.VIBRATION, "mm/s"),
    ("RPM Sensor", SensorType.RPM, "rpm"),
    ("Energy Sensor", SensorType.ENERGY, "kWh"),
]


def seed_database() -> None:
    with SessionLocal() as db:
        db.execute(delete(Sensor))
        db.execute(delete(Machine))
        db.execute(delete(ProductionLine))
        db.execute(delete(Factory))

        machine_counter = 1

        for factory_data in FACTORIES:
            factory = Factory(**factory_data)
            db.add(factory)
            db.flush()

            for line_name in PRODUCTION_LINES:
                production_line = ProductionLine(
                    name=line_name,
                    factory_id=factory.id,
                )
                db.add(production_line)
                db.flush()

                for machine_index in range(1, 6):
                    machine = Machine(
                        name=f"{line_name} Machine {machine_index}",
                        serial_number=f"MCH-{machine_counter:04d}",
                        manufacturer="Siemens",
                        model_number=f"NX-{100 + machine_index}",
                        status=MachineStatus.RUNNING,
                        installation_date=date(2024, 1, machine_index),
                        production_line_id=production_line.id,
                    )

                    db.add(machine)
                    db.flush()

                    for sensor_name, sensor_type, unit in SENSOR_CONFIG:
                        sensor = Sensor(
                            name=f"{sensor_name} - {machine.serial_number}",
                            sensor_type=sensor_type,
                            unit=unit,
                            machine_id=machine.id,
                        )
                        db.add(sensor)

                    machine_counter += 1

        db.commit()

        print("Seed completed successfully.")
        print(f"Factories created: {len(FACTORIES)}")
        print(
            "Production lines created:",
            len(FACTORIES) * len(PRODUCTION_LINES),
        )
        print(
            "Machines created:",
            len(FACTORIES) * len(PRODUCTION_LINES) * 5,
        )
        print(
            "Sensors created:",
            len(FACTORIES) * len(PRODUCTION_LINES) * 5 * len(SENSOR_CONFIG),
        )


if __name__ == "__main__":
    seed_database()
