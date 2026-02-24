const memory = new Map<string, { count: number; resetAt: number }>();

export function checkRateLimit(key: string, max = 60, windowMs = 60_000) {
  const now = Date.now();
  const item = memory.get(key);
  if (!item || item.resetAt < now) {
    memory.set(key, { count: 1, resetAt: now + windowMs });
    return true;
  }
  if (item.count >= max) return false;
  item.count += 1;
  return true;
}
