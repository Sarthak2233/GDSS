'use client';

import React, { useState, useMemo, useRef, useEffect } from 'react';
import { Search, X, Code2, Box, Cpu, FileCode } from 'lucide-react';

export interface SymbolItem {
  id: string;
  name: string;
  type: string;
  location: string;
}

export interface SymbolSearchPickerProps {
  symbols: SymbolItem[];
  onSelectSymbol: (symbolId: string, name: string) => void;
  placeholder?: string;
  className?: string;
}

export function SymbolSearchPicker({
  symbols,
  onSelectSymbol,
  placeholder = 'Search & inspect symbols (e.g., TransformExtractor)...',
  className = '',
}: SymbolSearchPickerProps) {
  const [query, setQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  // Filter symbols based on substring query (limit to 12 for performance and UI clarity)
  const filteredSymbols = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return [];
    return symbols
      .filter(
        (s) =>
          s.name.toLowerCase().includes(q) ||
          s.location.toLowerCase().includes(q) ||
          s.id.toLowerCase().includes(q)
      )
      .slice(0, 12);
  }, [symbols, query]);

  // Handle outside click to close dropdown
  useEffect(() => {
    function handleOutsideClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleOutsideClick);
    return () => document.removeEventListener('mousedown', handleOutsideClick);
  }, []);

  const handleSelect = (sym: SymbolItem) => {
    onSelectSymbol(sym.id, sym.name);
    setQuery('');
    setIsOpen(false);
    setActiveIndex(0);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!isOpen || filteredSymbols.length === 0) {
      if (e.key === 'ArrowDown' && query.trim()) {
        setIsOpen(true);
      }
      return;
    }

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActiveIndex((prev) => (prev + 1) % filteredSymbols.length);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActiveIndex((prev) => (prev - 1 + filteredSymbols.length) % filteredSymbols.length);
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (filteredSymbols[activeIndex]) {
        handleSelect(filteredSymbols[activeIndex]);
      }
    } else if (e.key === 'Escape') {
      setIsOpen(false);
    }
  };

  const getSymbolIcon = (type: string) => {
    const t = type.toLowerCase();
    if (t === 'class') return <Box className="h-3.5 w-3.5 text-purple-400" aria-hidden="true" />;
    if (t === 'method') return <Cpu className="h-3.5 w-3.5 text-amber-400" aria-hidden="true" />;
    if (t === 'import') return <FileCode className="h-3.5 w-3.5 text-emerald-400" aria-hidden="true" />;
    return <Code2 className="h-3.5 w-3.5 text-blue-400" aria-hidden="true" />;
  };

  const getBadgeColor = (type: string) => {
    const t = type.toLowerCase();
    if (t === 'class') return 'bg-purple-500/10 text-purple-400 border-purple-500/20';
    if (t === 'method') return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
    if (t === 'import') return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
    return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
  };

  return (
    <div ref={containerRef} className={`relative w-full ${className}`}>
      <div className="relative flex items-center">
        <Search
          className="absolute left-3.5 h-4 w-4 text-muted-foreground pointer-events-none"
          aria-hidden="true"
        />
        <input
          type="text"
          role="combobox"
          aria-expanded={isOpen && filteredSymbols.length > 0}
          aria-autocomplete="list"
          aria-controls="symbol-search-listbox"
          aria-activedescendant={
            isOpen && filteredSymbols[activeIndex]
              ? `symbol-option-${filteredSymbols[activeIndex].id}`
              : undefined
          }
          aria-label="Search and inspect repository symbols"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setIsOpen(true);
            setActiveIndex(0);
          }}
          onFocus={() => {
            if (query.trim()) setIsOpen(true);
          }}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          className="w-full h-10 pl-10 pr-10 rounded-lg border border-border bg-card/90 backdrop-blur-sm text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary transition-all"
        />
        {query && (
          <button
            type="button"
            onClick={() => {
              setQuery('');
              setIsOpen(false);
            }}
            className="absolute right-3 p-1 rounded-md text-muted-foreground hover:text-foreground transition-colors"
            aria-label="Clear search query"
          >
            <X className="h-3.5 w-3.5" aria-hidden="true" />
          </button>
        )}
      </div>

      {/* Autocomplete Dropdown Listbox */}
      {isOpen && filteredSymbols.length > 0 && (
        <ul
          id="symbol-search-listbox"
          role="listbox"
          className="absolute left-0 right-0 top-11 z-50 max-h-80 overflow-y-auto rounded-lg border border-border bg-card/95 backdrop-blur-md shadow-xl py-1.5 divide-y divide-border/40"
        >
          {filteredSymbols.map((sym, idx) => {
            const isSelected = idx === activeIndex;
            return (
              <li
                key={sym.id}
                id={`symbol-option-${sym.id}`}
                role="option"
                aria-selected={isSelected}
                onClick={() => handleSelect(sym)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') handleSelect(sym);
                }}
                onMouseEnter={() => setActiveIndex(idx)}
                className={`flex items-center justify-between gap-3 px-3.5 py-2.5 cursor-pointer text-sm transition-colors ${
                  isSelected
                    ? 'bg-primary/15 text-foreground font-medium'
                    : 'hover:bg-secondary/60 text-foreground'
                }`}
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  {getSymbolIcon(sym.type)}
                  <span className="truncate">{sym.name}</span>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <span
                    className={`text-[10px] uppercase font-semibold px-1.5 py-0.5 rounded border ${getBadgeColor(
                      sym.type
                    )}`}
                  >
                    {sym.type || 'symbol'}
                  </span>
                  <span className="text-xs text-muted-foreground truncate max-w-[140px] hidden sm:inline">
                    {sym.location}
                  </span>
                </div>
              </li>
            );
          })}
        </ul>
      )}

      {/* Empty State when Query yields zero results */}
      {isOpen && query.trim() && filteredSymbols.length === 0 && (
        <div
          role="region"
          aria-live="polite"
          className="absolute left-0 right-0 top-11 z-50 rounded-lg border border-border bg-card/95 backdrop-blur-md shadow-xl px-4 py-3 text-center text-xs text-muted-foreground"
        >
          No repository symbols matching &ldquo;{query}&rdquo;. Try another name or keyword.
        </div>
      )}
    </div>
  );
}
