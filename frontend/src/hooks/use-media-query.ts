import { useEffect, useState } from "react";

/** Reactively track a CSS media query. */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(
    () => window.matchMedia(query).matches,
  );

  useEffect(() => {
    const media = window.matchMedia(query);
    const listener = (event: MediaQueryListEvent) => setMatches(event.matches);
    media.addEventListener("change", listener);
    setMatches(media.matches);
    return () => media.removeEventListener("change", listener);
  }, [query]);

  return matches;
}

export const useIsDesktop = () => useMediaQuery("(min-width: 1024px)");
