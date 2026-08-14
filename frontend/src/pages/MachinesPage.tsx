import { useState } from "react";
import { useSearchParams } from "react-router-dom";

import type { MachineFleetItem } from "../types/api";

type MachinesPageProps = {
  machines: MachineFleetItem[];
  error: string;
  onSelectMachine: (machineId: string) => void;
  initialStatusFilter: string;
};

function MachinesPage({
  machines,
  error,
  onSelectMachine,
  initialStatusFilter,
}: MachinesPageProps) {
  const [search, setSearch] = useState("");
  const [searchParams, setSearchParams] = useSearchParams();

  const statusFilter =
    searchParams.get("status") ?? initialStatusFilter;

  const productionLineFilter =
    searchParams.get("line") ?? "ALL";

  const productionLines = Array.from(
    new Set(machines.map((machine) => machine.production_line)),
  ).sort();

  const filteredMachines = machines.filter((machine) => {
    const matchesSearch =
      machine.name.toLowerCase().includes(search.toLowerCase()) ||
      machine.serial_number
        .toLowerCase()
        .includes(search.toLowerCase()) ||
      machine.production_line
        .toLowerCase()
        .includes(search.toLowerCase());

    const matchesStatus =
      statusFilter === "ALL" ||
      machine.health_status === statusFilter;

    const matchesProductionLine =
      productionLineFilter === "ALL" ||
      machine.production_line === productionLineFilter;

    return (
      matchesSearch &&
      matchesStatus &&
      matchesProductionLine
    );
  });

  if (error) {
    return <div className="status-message">Error: {error}</div>;
  }

  return (
    <>
      <header className="page-header">
        <div>
          <p className="eyebrow">Manufacturing Assets</p>
          <h1>Machine Fleet</h1>
          <p className="subtitle">
            Current health status across all production equipment.
          </p>
        </div>
      </header>

      <div className="filters-bar">
        <input
          className="search-input"
          type="text"
          placeholder="Search machine, serial number, or production line..."
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />

        <select
          className="filter-select"
          value={productionLineFilter}
          onChange={(event) => {
            const next = new URLSearchParams(searchParams);

            if (event.target.value === "ALL") {
              next.delete("line");
            } else {
              next.set("line", event.target.value);
            }

            setSearchParams(next);
          }}
        >
          <option value="ALL">All Production Lines</option>

          {productionLines.map((productionLine) => (
            <option
              key={productionLine}
              value={productionLine}
            >
              {productionLine}
            </option>
          ))}
        </select>

        <select
          className="filter-select"
          value={statusFilter}
          onChange={(event) => {
            const next = new URLSearchParams(searchParams);

            if (event.target.value === "ALL") {
              next.delete("status");
            } else {
              next.set("status", event.target.value);
            }

            setSearchParams(next);
          }}
        >
          <option value="ALL">All Statuses</option>
          <option value="HEALTHY">Healthy</option>
          <option value="WARNING">Warning</option>
          <option value="CRITICAL">Critical</option>
        </select>
      </div>

      <p className="results-count">
        Showing {filteredMachines.length} of {machines.length} machines
      </p>

      <div className="machine-table-wrapper">
        <table className="machine-table">
          <thead>
            <tr>
              <th>Machine</th>
              <th>Serial Number</th>
              <th>Production Line</th>
              <th>Status</th>
              <th>Health</th>
            </tr>
          </thead>

          <tbody>
            {filteredMachines.map((machine) => (
              <tr
                key={machine.id}
                className="clickable-row"
                onClick={() => onSelectMachine(machine.id)}
              >
                <td>{machine.name}</td>
                <td>{machine.serial_number}</td>
                <td>{machine.production_line}</td>

                <td>
                  <span
                    className={`health-badge ${machine.health_status.toLowerCase()}`}
                  >
                    {machine.health_status}
                  </span>
                </td>

                <td>{machine.health_score}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

export default MachinesPage;
