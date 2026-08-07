from enum import StrEnum


class MachineStatus(StrEnum):
    RUNNING = "RUNNING"
    IDLE = "IDLE"
    MAINTENANCE = "MAINTENANCE"
    OFFLINE = "OFFLINE"


class SensorType(StrEnum):
    TEMPERATURE = "TEMPERATURE"
    PRESSURE = "PRESSURE"
    VIBRATION = "VIBRATION"
    RPM = "RPM"
    ENERGY = "ENERGY"
