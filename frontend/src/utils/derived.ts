/**
 * Deterministic client-side derivations for display fields the backend does
 * not track yet (reserved stock, incoming shipments, node health). Values are
 * stable per entity id, so the UI stays consistent between renders and
 * sessions until the real fields land in the API.
 */

/** Hash a string to a stable float in [0, 1). */
export function stableFraction(seed: string, salt = ""): number {
  const input = `${seed}:${salt}`;
  let hash = 2166136261;
  for (let i = 0; i < input.length; i++) {
    hash ^= input.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return ((hash >>> 0) % 10_000) / 10_000;
}

export function stableInt(seed: string, salt: string, min: number, max: number): number {
  return Math.floor(min + stableFraction(seed, salt) * (max - min + 1));
}

/** Reserved units: 4–18% of available stock. */
export function derivedReserved(id: string, quantity: number): number {
  return Math.round(quantity * (0.04 + stableFraction(id, "reserved") * 0.14));
}

/** Incoming units: zero for ~30% of rows, otherwise 10–60% of reorder point. */
export function derivedIncoming(id: string, reorderPoint: number): number {
  const fraction = stableFraction(id, "incoming");
  if (fraction < 0.3) return 0;
  return Math.round(reorderPoint * (0.1 + fraction * 0.5));
}

/** Node health score 55–99. */
export function derivedHealth(id: string): number {
  return stableInt(id, "health", 55, 99);
}

/** Lead time 2–28 days for nodes without one. */
export function derivedLeadTime(id: string): number {
  return stableInt(id, "lead", 2, 28);
}

/** Outbound units/day for warehouses. */
export function derivedOutgoing(id: string, currentInventory: number): number {
  return Math.round(currentInventory * (0.02 + stableFraction(id, "out") * 0.06));
}
