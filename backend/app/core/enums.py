from enum import StrEnum


class MachineStatus(StrEnum):
    RUNNING = "RUNNING"
    IDLE = "IDLE"
    MAINTENANCE = "MAINTENANCE"
    OFFLINE = "OFFLINE"
