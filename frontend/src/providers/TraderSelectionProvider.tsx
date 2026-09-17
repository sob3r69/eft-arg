import type { ReactNode } from 'react';
import { createContext, use, useMemo, useState } from 'react';

interface TraderSelectionContextValue {
  selectedTraderSlug:    string | null;
  setSelectedTraderSlug: (slug: string) => void;
}

const TraderSelectionContext = createContext<TraderSelectionContextValue | null>(null);

interface TraderSelectionProviderProps {
  children: ReactNode;
}

export function TraderSelectionProvider({
  children,
}: TraderSelectionProviderProps) {
  const [selectedTraderSlug, setSelectedTraderSlug] = useState<string | null>(null);

  const value = useMemo(() => ({
    selectedTraderSlug,
    setSelectedTraderSlug,
  }), [selectedTraderSlug]);

  return (
    <TraderSelectionContext value={value}>
      {children}
    </TraderSelectionContext>
  );
}

export function useTraderSelection() {
  const context = use(TraderSelectionContext);

  if (!context) {
    throw new Error('useTraderSelection must be used within TraderSelectionProvider');
  }

  return context;
}
