import React from 'react';

interface Column<T> {
  header: string;
  accessor: (item: T) => React.ReactNode;
  className?: string;
}

interface TableProps<T> {
  columns: Column<T>[];
  data: T[];
  caption?: string;
  keyExtractor: (item: T) => string;
}

export function Table<T>({ columns, data, caption, keyExtractor }: TableProps<T>) {
  return (
    <div className="border border-hairline bg-surface rounded-[2px] overflow-hidden">
      {caption && (
        <div className="px-4 py-2 border-b border-hairline bg-paper/60 font-mono text-xs uppercase text-ink-muted">
          {caption}
        </div>
      )}
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-hairline bg-paper/30 font-mono text-[11px] text-ink-muted uppercase tracking-wider">
              {columns.map((col, i) => (
                <th key={i} className={`p-3 font-medium ${col.className || ''}`}>
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-hairline font-sans text-xs text-ink">
            {data.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="p-4 text-center font-mono text-ink-muted">
                  NO RECORDS FOUND
                </td>
              </tr>
            ) : (
              data.map((item) => (
                <tr key={keyExtractor(item)} className="hover:bg-paper/40 transition-colors">
                  {columns.map((col, i) => (
                    <td key={i} className={`p-3 ${col.className || ''}`}>
                      {col.accessor(item)}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
