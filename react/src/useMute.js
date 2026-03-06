import React, { createContext, useContext, useState } from 'react';

const MuteContext = createContext();

/**
 * Wrap your app with <MuteProvider> to provide global mute state.
 */
export function MuteProvider({ children }) {
  const [muted, setMuted] = useState(false);
  return (
    <MuteContext.Provider value={{ muted, setMuted }}>
      {children}
    </MuteContext.Provider>
  );
}

/**
 * Hook to access mute state.
 * const { muted, setMuted } = useMute();
 */
export function useMute() {
  const ctx = useContext(MuteContext);
  if (!ctx) {
    throw new Error('useMute must be used within a MuteProvider');
  }
  return ctx;
}
