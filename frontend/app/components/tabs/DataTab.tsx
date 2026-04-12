import { EmptyState } from "./EmptyState";
import { cn } from "@/lib/utils";

interface DataTabProps {
  rows?: Record<string, unknown>[];
}

export function DataTab({ rows }: DataTabProps) {
  if (!rows?.length) {
    return <EmptyState>No structured data for this response</EmptyState>;
  }

  const columns = Object.keys(rows[0]);

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse font-mono text-[10px]">
        <thead>
          <tr>
            {columns.map((column) => (
              <th
                key={column}
                className="border-b border-border-0 px-2 py-[5px] text-left text-[9px] uppercase text-text-3"
              >
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={rowIndex}>
              {columns.map((column) => {
                const value = row[column];
                const isNumeric = typeof value === "number";
                const textValue = formatCellValue(value);

                return (
                  <td
                    key={column}
                    className={cn(
                      "border-b border-bg-2 px-2 py-[4px] text-text-1",
                      isNumeric && "text-right font-medium text-text-0",
                      typeof value === "string" &&
                        value.startsWith("+") &&
                        "text-green",
                      typeof value === "string" &&
                        value.startsWith("-") &&
                        "text-red"
                    )}
                  >
                    {textValue}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function formatCellValue(value: unknown): string {
  if (typeof value === "number") {
    if (Math.abs(value) < 1) {
      return value.toFixed(3);
    }

    return new Intl.NumberFormat("en-GB").format(value);
  }

  if (typeof value === "string") {
    return value;
  }

  if (value === null || typeof value === "undefined") {
    return "";
  }

  return String(value);
}
